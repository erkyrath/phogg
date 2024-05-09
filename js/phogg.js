'use strict';

var alltags = [];
var alltagmap = new Map();

var allpics = [];
var allpicmap = new Map();

var selected = new Set();
var displayed = new Set();
var lastselectanchor = -1;

var imagesize = 180; // 110, 180, 360

var filtertext = null;

function rebuild_pics()
{
    displayed.clear();
    lastselectanchor = -1;
    
    var ls = [];
    var index = 0;
    for (var pic of allpics) {
        pic.index = -1;

        if (filtertext != null) {
            var anymatch = false;
            for (var tag of pic.tags) {
                if (tag.includes(filtertext)) {
                    anymatch = true;
                    break;
                }
            }
            if (!anymatch)
                continue;
        }
        
        ls.push(pic);
        displayed.add(pic.guid);
        pic.index = index;
        index++;
    }
    
    var parel = $('.PhotoGrid');
    parel.empty();
    for (var pic of ls) {
        parel.append(build_pic_el(pic));
    }

    rebuild_selected_tags();
}

function build_pic_el(pic)
{
    var cellel = $('<div>', { class:'PhotoCell', id:'cell-'+pic.guid });
    cellel.append($('<div>', { class:'Filename' }).text(pic.pathname));
    var outel = $('<a>', { href:'testpics/'+pic.pathname, target:'_blank' }).text('\u21D7');
    cellel.append($('<div>', { class:'OutButton' }).append(outel));

    var width, height;
    if (pic.aspect > 1) {
        width = imagesize;
        height = Math.floor(imagesize / pic.aspect);
    }
    else {
        height = imagesize;
        width = Math.floor(imagesize * pic.aspect);
    }
    
    var imgel = $('<img>', { class:'Photo', id:'img-'+pic.guid, loading:'lazy', src:'testpics/'+pic.pathname, width:width, height:height });
    cellel.append(imgel);
    imgel.on('click', { guid:pic.guid, index:pic.index }, evhan_click_image);

    cellel.append($('<div>', { class:'Date' }).text(pic.texttime));
    var tagtext = '';
    if (pic.tags) {
        var showtags = [];
        for (var tag of pic.tags) {
            if (!alltagmap.get(tag).autogen) {
                showtags.push(tag);
            }
        }
        if (showtags.length)
            tagtext = showtags.join(', ');
    }
    cellel.append($('<div>', { class:'Tags' }).text(tagtext));
    
    var boxel = $('<div>', { class:'PhotoCellBox', id:'cellbox-'+pic.guid });
    if (selected.has(pic.guid))
        boxel.addClass('Selected');
    boxel.append($('<div>', { class:'PhotoCellGap' }));
    boxel.append(cellel);
    boxel.append($('<div>', { class:'PhotoCellGap' }));

    return boxel;
}

function resize_all_pics()
{
    for (var pic of allpics) {
        var imgel = $('#img-'+pic.guid);
        if (imgel.length) {
            var width, height;
            if (pic.aspect > 1) {
                width = imagesize;
                height = Math.floor(imagesize / pic.aspect);
            }
            else {
                height = imagesize;
                width = Math.floor(imagesize * pic.aspect);
            }
            imgel.width(width);
            imgel.height(height);
        }
    }
}

function rebuild_selected_tags()
{
    var tagset = new Map();
    var viscount = 0;

    for (var guid of selected) {
        if (!displayed.has(guid))
            continue;
        var pic = allpicmap.get(guid);
        viscount++;
        if (pic.tags) {
            for (var tag of pic.tags) {
                if (!tagset.has(tag))
                    tagset.set(tag, 1);
                else
                    tagset.set(tag, 1+tagset.get(tag));
            }
        }
    }
    
    var boxel = $('.SelectedTagBox');
    boxel.empty();

    var allchecks = $('.Tag input');
    allchecks.prop('checked', false);
    allchecks.prop('indeterminate', null);

    if (tagset.size == 0) {
        var el = $('<p>', { class:'Info' }).text('No photos selected');
        boxel.append(el);
        return;
    }

    var tagls = Array.from(tagset.keys());
    tagls.sort(tagname_sort_func);

    for (var tag of tagls) {
        var el = build_tag_el(tag, false);
        boxel.append(el);
    }

    for (var tag of tagls) {
        var tagkey = tag.replace(':', '__');
        var chel1 = $('#seltag-'+tagkey+' input');
        var chel2 = $('#alltag-'+tagkey+' input');
        if (tagset.get(tag) == viscount) {
            chel1.prop('checked', true);
            chel2.prop('checked', true);
            chel1.prop('indeterminate', false);
            chel2.prop('indeterminate', false);
        }
        else {
            chel1.prop('checked', false);
            chel2.prop('checked', false);
            chel1.prop('indeterminate', true);
            chel2.prop('indeterminate', true);
        }
    }
}

function build_tag_el(tag, allbox)
{
    var tagkey = tag.replace(':', '__');
    var id = (allbox ? 'alltag-'+tagkey : 'seltag-'+tagkey);
    var cla = (allbox ? 'AllBoxTag' : 'SelBoxTag');
    
    var el = $('<div>', { id:id, class:'Tag '+cla });
    var checkel = $('<input>', { type:'checkbox' });
    el.append(checkel);
    el.append($('<span>').text(tag));

    var tagobj = alltagmap.get(tag);
    if (!(tagobj && tagobj.autogen)) {
        el.on('click', { tag:tag }, evhan_click_tag);
    }

    return el;
}

function adjust_selected_pics(clearall, guids)
{
    if (clearall) {
        $('.PhotoCellBox').removeClass('Selected');
    }

    for (var guid of guids) {
        if (selected.has(guid)) {
            $('#cellbox-'+guid).addClass('Selected');
        }
        else {
            $('#cellbox-'+guid).removeClass('Selected');
        }
    }

    rebuild_selected_tags();
}

function rebuild_alltags()
{
    var boxel = $('.AllTagBox');
    boxel.empty();
    for (var tagobj of alltags) {
        var tag = tagobj.tag;
        var el = build_tag_el(tag, true);
        boxel.append(el);
    }
}

function evhan_api_getpics(data, status, jqreq)
{
    alltags = [];
    alltagmap.clear();

    if (data.tags) {
        alltags = data.tags;
        for (var tag of alltags) {
            alltagmap.set(tag.tag, tag);
        }
    }
    
    allpics = [];
    allpicmap.clear();
    displayed.clear();
    selected.clear();
    lastselectanchor = -1;
    
    if (data.pics) {
        allpics = data.pics;
        for (var pic of allpics) {
            allpicmap.set(pic.guid, pic);
            pic.aspect = pic.width / pic.height;
            pic.index = -1;
        }
    }

    alltags.sort(tagobj_sort_func);
    allpics.sort(function(p1, p2) { return p2.timestamp - p1.timestamp; });

    rebuild_alltags();
    rebuild_pics();
}

function evhan_api_error(jqreq, status, error)
{
    console.log('### request error', jqreq.status, status, error);
}

function evhan_select_size(ev)
{
    var size = ev.data.size;
    var key = ev.data.key;

    if (size == imagesize) {
        return;
    }

    var el = $('.PhotoGrid');
    el.removeClass('SizeLarge');
    el.removeClass('SizeMedium');
    el.removeClass('SizeSmall');
    el.addClass('Size'+key);
    
    imagesize = size;
    resize_all_pics();
}

function evhan_filtertext_change()
{
    var filter = $('#filtertext').val();
    if (!filter.length)
        filter = null;

    if (filtertext != filter) {
        filtertext = filter;
        rebuild_pics();
    }
}

function evhan_filtertext_commit()
{
    var filter = $('#filtertext').val();
    if (!filter.length)
        return;
    
    console.log('### filter commit:', filter);
}

function evhan_click_image(ev)
{
    var guid = ev.data.guid;
    var index = ev.data.index;

    ev.preventDefault();
    ev.stopPropagation();

    if (ev.metaKey) {
        if (!selected.has(guid)) {
            lastselectanchor = index;
            selected.add(guid);
        }
        else {
            selected.delete(guid);
        }
        adjust_selected_pics(false, [ guid ]);
    }
    else if (ev.shiftKey) {
        if (lastselectanchor == -1) {
            lastselectanchor = index;
            //### also track whether this is a meta-anchor or reg-anchor?
            if (!selected.has(guid)) {
                selected.add(guid);
                adjust_selected_pics(false, [ guid ]);
            }
        }
        else {
            var newls = [];
            if (index < lastselectanchor) {
                for (var guid of displayed) {
                    var pic = allpicmap.get(guid);
                    if (pic.index >= index && pic.index <= lastselectanchor)
                        newls.push(guid);
                }
            }
            else {
                for (var guid of displayed) {
                    var pic = allpicmap.get(guid);
                    if (pic.index >= lastselectanchor && pic.index <= index)
                        newls.push(guid);
                }
            }
            selected.clear();
            for (var guid of newls) {
                selected.add(guid);
            }
            adjust_selected_pics(true, newls);
        }
    }
    else {
        lastselectanchor = index;
        if (!selected.has(guid) || (selected.size > 1)) {
            selected.clear();
            selected.add(guid);
            adjust_selected_pics(true, [ guid ]);
        }
    }
}

function evhan_click_tag(ev)
{
    var tag = ev.data.tag;
    console.log('### tag', tag);
}

function evhan_click_background(ev)
{
    var target = $(ev.target);
    if (!(target.hasClass('PhotoGrid') || target.hasClass('PhotoCellGap')))
        return;
    
    ev.preventDefault();
    ev.stopPropagation();

    lastselectanchor = -1;
    if (selected.size) {
        selected.clear();
        adjust_selected_pics(true, []);
    }
}

function tagname_sort_func(t1, t2)
{
    var tag1 = alltagmap.get(t1);
    var tag2 = alltagmap.get(t2);

    var auto1 = tag1 ? tag1.autogen : false;
    var auto2 = tag2 ? tag2.autogen : false;
    
    if (auto1 && !auto2)
        return 1;
    if (auto2 && !auto1)
        return -1;
    return t1.localeCompare(t2);
}

function tagobj_sort_func(tag1, tag2)
{
    var auto1 = tag1 ? tag1.autogen : false;
    var auto2 = tag2 ? tag2.autogen : false;
    
    if (auto1 && !auto2)
        return 1;
    if (auto2 && !auto1)
        return -1;
    return tag1.tag.localeCompare(tag2.tag);
}

$(document).ready(function() {
    $('#imgsize-s').on('change', { size:110, key:'Small' }, evhan_select_size);
    $('#imgsize-m').on('change', { size:180, key:'Medium' }, evhan_select_size);
    $('#imgsize-l').on('change', { size:360, key:'Large' }, evhan_select_size);

    $('#filtertext').on('input', evhan_filtertext_change);
    $('#filtertext').on('change', evhan_filtertext_commit);

    $('.PhotoGrid').on('click', evhan_click_background);

    //### undo? https://github.com/samthor/undoer
    
    jQuery.ajax('/phogg/api/getpics', {
        dataType: 'json',
        success: evhan_api_getpics,
        error: evhan_api_error,
    });
});
