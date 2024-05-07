'use strict';

function evhan_api_getpics(data, status, jqreq)
{
    console.log('### request success', status, data);
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
