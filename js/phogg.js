'use strict';

var imagesize = 190;

function build_pic_el(pic)
{
    var cellel = $('<div>', { class:'PhotoCell' });
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
    
    var imgel = $('<img>', { class:'Photo', loading:'lazy', src:'testpics/'+pic.pathname, width:width, height:height });
    cellel.append(imgel);
    imgel.on('click', { guid:pic.guid, index:pic.index }, evhan_imageclick);

    cellel.append($('<div>', { class:'Date' }).text(pic.texttime));
    var tagtext = '';
    if (pic.tags) {
	tagtext = pic.tags.join(', ');
    }
    cellel.append($('<div>', { class:'Tags' }).text(tagtext));
    
    var boxel = $('<div>', { class:'PhotoCellBox' });
    boxel.append($('<div>', { class:'PhotoCellGap' }));
    boxel.append(cellel);
    boxel.append($('<div>', { class:'PhotoCellGap' }));

    return boxel;
}

function evhan_api_getpics(data, status, jqreq)
{
    console.log('### request success', status, data);
    if (data.pics) {
	var index = 0;
	for (var pic of data.pics) {
	    pic.aspect = pic.width / pic.height;
	    pic.index = index;
	    index++;
	}
	
	var parel = $('.PhotoGrid');
	parel.empty();
	for (var pic of data.pics) {
	    parel.append(build_pic_el(pic));
	}
    }
}

function evhan_api_error(jqreq, status, error)
{
    console.log('### request error', jqreq.status, status, error);
}

function evhan_imageclick(ev)
{
    var guid = ev.data.guid;
    var index = ev.data.index;
    console.log('### image click', index, guid, ev.metaKey, ev.shiftKey);
}

$(document).ready(function() {
    jQuery.ajax('/phogg/api/getpics', {
	dataType: 'json',
	success: evhan_api_getpics,
	error: evhan_api_error,
    });
});
