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

    cellel.append($('<div>', { class:'Date' }).text(pic.texttime));
    
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
	for (var pic of data.pics) {
	    pic.aspect = pic.width / pic.height;
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

$(document).ready(function() {
    jQuery.ajax('/phogg/api/getpics', {
	dataType: 'json',
	success: evhan_api_getpics,
	error: evhan_api_error,
    });
});
