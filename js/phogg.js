'use strict';

var alltags = [];
var alltagmap = new Map();

var allpics = [];
var allpicmap = new Map();

var selected = new Set();
var displayed = new Set();

var imagesize = 180; // 110, 180, 360

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
    imgel.on('click', { guid:pic.guid, index:pic.index }, evhan_imageclick);

    cellel.append($('<div>', { class:'Date' }).text(pic.texttime));
    var tagtext = '';
    if (pic.tags) {
        tagtext = pic.tags.join(', ');
    }
    cellel.append($('<div>', { class:'Tags' }).text(tagtext));
    
    var boxel = $('<div>', { class:'PhotoCellBox', id:'cellbox-'+pic.guid });
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
    
    if (data.pics) {
        allpics = data.pics;
        
        var index = 0;
        for (var pic of allpics) {
            allpicmap.set(pic.guid, pic);
            
            pic.aspect = pic.width / pic.height;
            pic.index = index;
            index++;
        }
    }

    allpics.sort(function(p1, p2) { return p2.timestamp - p1.timestamp; });

    var parel = $('.PhotoGrid');
    parel.empty();
    for (var pic of allpics) {
        parel.append(build_pic_el(pic));
    }
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
    console.log('### filter:', filter);
}

function evhan_filtertext_commit()
{
    var filter = $('#filtertext').val();
    console.log('### filter commit:', filter);
}

function evhan_imageclick(ev)
{
    var guid = ev.data.guid;
    var index = ev.data.index;
    console.log('### image click', index, guid, ev.metaKey, ev.shiftKey);

    var box = $('#cellbox-'+guid);
    if (box.length) {
        if (!box.hasClass('Selected'))
            $('#cellbox-'+guid).addClass('Selected');
        else
            $('#cellbox-'+guid).removeClass('Selected');
    }
}

$(document).ready(function() {
    $('#imgsize-s').on('change', { size:110, key:'Small' }, evhan_select_size);
    $('#imgsize-m').on('change', { size:180, key:'Medium' }, evhan_select_size);
    $('#imgsize-l').on('change', { size:360, key:'Large' }, evhan_select_size);

    $('#filtertext').on('input', evhan_filtertext_change);
    $('#filtertext').on('change', evhan_filtertext_commit);
    
    jQuery.ajax('/phogg/api/getpics', {
        dataType: 'json',
        success: evhan_api_getpics,
        error: evhan_api_error,
    });
});
