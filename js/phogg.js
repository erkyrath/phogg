'use strict';

var alltags = [];
var alltagmap = new Map();
var alltagmarks = new Map();
var recenttags = [];

var allpics = [];
var allpicmap = new Map();

var selected = new Set();
var displayed = new Set();
var lastselectanchor = -1;

var imagesize = 180; // 110, 180, 360

var filtertext = null;
var filtertags = [];

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

    rebuild_and_mark_tags();
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

function rebuild_filtertags()
{
    $('.FilterControl .Tag').remove();
    for (var tag of filtertags) {
        var el = build_filtertag_el(tag);
        $('.FilterControl').append(el);
    }
}

function rebuild_and_mark_tags()
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

    var boxel = $('.RecentTagBox');
    boxel.empty();

    for (var tag of recenttags) {
        var el = build_tag_el(tag, 'rectag');
        boxel.append(el);
    }
    
    var boxel = $('.SelectedTagBox');
    boxel.empty();

    alltagmarks.clear();
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
        var el = build_tag_el(tag, 'seltag');
        boxel.append(el);
    }

    for (var tag of tagls) {
        var tagkey = tag.replace(':', '__');
        var tagels = $('.Tag__'+tagkey+' input');
        if (tagset.get(tag) == viscount) {
            alltagmarks.set(tag, 'ALL');
            tagels.prop('checked', true);
            tagels.prop('indeterminate', false);
        }
        else {
            alltagmarks.set(tag, 'SOME');
            tagels.prop('checked', false);
            tagels.prop('indeterminate', true);
        }
    }
}

function build_tag_el(tag, box)
{
    var tagkey = tag.replace(':', '__');
    var id = box+'-'+tagkey;
    
    var cla = 'Tag ' + 'Tag__'+tagkey;
    if (box == 'alltag')
        cla += ' AllBoxTag';
    else if (box == 'rectag')
        cla += ' RecentBoxTag';
    else if (box == 'seltag')
        cla += ' SelBoxTag';
    
    var el = $('<div>', { id:id, class:cla });
    var checkel = $('<input>', { type:'checkbox' });
    el.append(checkel);
    el.append($('<span>').text(tag));

    var tagobj = alltagmap.get(tag);
    if (!(tagobj && tagobj.autogen)) {
        el.on('click', { tag:tag }, evhan_click_tag);
    }
    else {
        el.addClass('AutoGen');
        checkel.prop('disabled', true);
    }

    return el;
}

function build_filtertag_el(tag)
{
    var tagkey = tag.replace(':', '__');

    var el = $('<div>', { id:'filtag__'+tagkey, class:'Tag' });
    el.append($('<span>').text(tag));

    var delel = $('<a>', { href:'#', class:'TagClose' }).text('\u22A0');
    delel.on('click', function(ev) {
        ev.preventDefault();
        remove_filter_tag(tag);
    });
    el.append(delel);
    
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

    rebuild_and_mark_tags();
}

function rebuild_alltags()
{
    var boxel = $('.AllTagBox');
    boxel.empty();
    for (var tagobj of alltags) {
        var tag = tagobj.tag;
        var el = build_tag_el(tag, 'alltag');
        boxel.append(el);
    }
}


function accept_new_tag(newtag)
{
    add_recent_tag(newtag);
    
    var guids = get_selected();

    if (guids.length == 0) {
        check_new_tag({ tag:newtag, autogen:false });
        rebuild_and_mark_tags();
    }
    else {
        var dat = {
            tag: newtag,
            guids: guids,
            flag: true,
        };

        console.log('### settags', dat);
        
        jQuery.ajax('/phogg/api/settags', {
            method: 'POST',
            dataType: 'json',
            data: dat,
            success: evhan_api_settags,
            error: evhan_api_error,
        });
    }
}

function check_new_tag(tag)
{
    if (alltagmap.get(tag.tag))
        return;

    console.log('### adding new tag', tag);
    alltags.push(tag);
    alltagmap.set(tag.tag, tag);
    alltags.sort(tagobj_sort_func);

    rebuild_alltags();
    rebuild_and_mark_tags();
}

function add_recent_tag(tag)
{
    if (!recenttags.includes(tag)) {
        recenttags.splice(0, 0, tag);
        rebuild_and_mark_tags();
    }
}

function add_filter_tag(tag)
{
    var pos = filtertags.indexOf(tag);
    if (pos < 0) {
        filtertags.push(tag);
        rebuild_filtertags();
    }
}

function remove_filter_tag(tag)
{
    var pos = filtertags.indexOf(tag);
    if (pos >= 0) {
        filtertags.splice(pos, 1);
        rebuild_filtertags();
    }
}

function get_selected()
{
    var guids = [];
    
    for (var guid of selected) {
        if (!displayed.has(guid))
            continue;
        guids.push(guid);
    }

    return guids;
}

function display_error(msg)
{
    console.log('Error: ' + msg);
    
    var el = $('<div>', { class:'ErrorMsg' }).text(msg);
    el.hide();
    $('#errorpane').append(el);

    el.slideDown(300).delay(2000).slideUp(300, function() {
        el.remove();
    });
}

function evhan_api_getpics(data, status, jqreq)
{
    if (data.error) {
        display_error('getpics: ' + data.error);
    }
    
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

function evhan_api_settags(data, status, jqreq)
{
    if (data.error) {
        display_error('settags: ' + data.error);
        return;
    }
    console.log('### response', data);
    
    var tag = data.tag;
    var guids = data.guids;
    var flag = data.flag;
    
    check_new_tag(tag);

    for (var guid of guids) {
        var pic = allpicmap.get(guid);
        if (!pic)
            continue;
        if (flag) {
            if (!pic.tags.includes(tag.tag)) {
                pic.tags.push(tag.tag);
            }
        }
        else {
            var pos = pic.tags.indexOf(tag.tag);
            if (pos >= 0) {
                pic.tags.splice(pos, 1);
            }
        }
    }

    //### or: bang the pic tags lines, then rebuild_and_mark_tags()
    rebuild_alltags();
    rebuild_pics();
}

function evhan_api_error(jqreq, status, error)
{
    display_error(jqreq.responseText);
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

function evhan_filtertext_keydown(ev)
{
    if (ev.key == 'Enter') {
        ev.preventDefault();
        
        var newtag = $('#filtertext').val();
        newtag = newtag.trim();
        
        //###$('#filtertext').val('');
        console.log('### commit filter', newtag);
        return;
    }
    
    if (ev.key == 'Tab') {
        ev.preventDefault();

        var newtag = $('#filtertext').val();
        newtag = newtag.trim();
        var val = tab_completion(newtag);
        $('#filtertext').val(val);

        return;
    }
}

function evhan_newtag_keydown(ev)
{
    if (ev.key == 'Enter') {
        ev.preventDefault();
        
        var newtag = $('#newtagtext').val();
        newtag = newtag.trim();
        
        $('#newtagtext').val('');
        
        if (newtag.length)
            accept_new_tag(newtag);
        return;
    }
    
    if (ev.key == 'Tab') {
        ev.preventDefault();

        var newtag = $('#newtagtext').val();
        newtag = newtag.trim();
        var val = tab_completion(newtag);
        $('#newtagtext').val(val);

        return;
    }
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

    var guids = get_selected();
    if (!guids.length)
        return;

    var flag = true;
    if (alltagmarks.get(tag) == 'ALL')
        flag = false;

    if (flag)
        add_recent_tag(tag);
    
    var dat = {
        tag: tag,
        guids: guids,
        flag: flag,
    };

    console.log('### settags', dat);
    
    jQuery.ajax('/phogg/api/settags', {
        method: 'POST',
        dataType: 'json',
        data: dat,
        success: evhan_api_settags,
        error: evhan_api_error,
    });
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

function tab_completion(val)
{
    var ls = [];
    
    for (var tag of alltags) {
        if (tag.tag.startsWith(val)) {
            ls.push(tag.tag);
        }
    }

    if (!ls.length)
        return val;

    var newval = ls.pop();
    for (var tag of ls) {
        while (true) {
            if (tag.startsWith(newval))
                break;
            newval = newval.slice(0, newval.length-1);
        }
        if (newval == val)
            return newval;
    }

    return newval;
}

$(document).ready(function() {
    $('#imgsize-s').on('change', { size:110, key:'Small' }, evhan_select_size);
    $('#imgsize-m').on('change', { size:180, key:'Medium' }, evhan_select_size);
    $('#imgsize-l').on('change', { size:360, key:'Large' }, evhan_select_size);

    $('#filtertext').on('input', evhan_filtertext_change);
    $('#filtertext').on('keydown', evhan_filtertext_keydown);
    
    $('#newtagtext').on('keydown', evhan_newtag_keydown);

    $('.PhotoGrid').on('click', evhan_click_background);

    //### undo? https://github.com/samthor/undoer
    
    jQuery.ajax('/phogg/api/getpics', {
        dataType: 'json',
        success: evhan_api_getpics,
        error: evhan_api_error,
    });
});
