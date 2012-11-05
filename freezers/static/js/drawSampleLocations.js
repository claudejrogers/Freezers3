var drawSampleLocations = function(slo, curr_samp) {
  var occup = slo;
  var currSample = curr_samp;
  for (var i=1; i<=occup.length; i++) {
  	var selector = "#canvas" + i;
  	var ctx = $(selector)[0].getContext("2d");
  	ctx.lineWidth = 2;
  	if (occup[i-1] === 1) {
  	  ctx.strokeStyle = "rgba(0,128,0,1)";
  	  ctx.fillStyle="rgba(108,205,0,1)";
  	} else {
  	  ctx.strokeStyle = "rgba(0,0,0,1)";
      ctx.fillStyle="#e0e0e0";
  	}
  	if (i === currSample) {
  	  ctx.lineWidth = 5;
  	  ctx.strokeStyle = "rgba(255,0,0,1)";
      ctx.fillStyle="#e0e0e0";
  	}
  	ctx.beginPath();
  	ctx.arc(15,15,10,0,Math.PI*2,true);
  	ctx.closePath();
  	ctx.stroke()
  	ctx.fill();
  }
}

var drawPreview = function(slo, curr_samp) {
  var occup = slo;
  var currSample = curr_samp;
  for (var i=1; i<=occup.length; i++) {
  	var selector = "#canvas" + i;
  	var ctx = $(selector)[0].getContext("2d");
  	ctx.lineWidth = 2;
  	if (occup[i-1] === 1) {
  	  ctx.strokeStyle = "rgba(0,128,0,1)";
  	  ctx.fillStyle="rgba(108,205,0,1)";
  	} else {
  	  ctx.strokeStyle = "rgba(0,0,0,1)";
      ctx.fillStyle="#e0e0e0";
  	}
  	if (i === currSample) {
  	  ctx.lineWidth = 5;
  	  ctx.strokeStyle = "rgba(255,0,0,1)";
      ctx.fillStyle="#e0e0e0";
  	}
  	ctx.beginPath();
  	ctx.arc(5,5,3.3,0,Math.PI*2,true);
  	ctx.closePath();
  	ctx.stroke()
  	ctx.fill();
  }
}
var drawAliquots = function(alonum) {
  for (var i=1; i<=alonum; i++) {
  	var selector = "#canv" + i;
  	var ctx = $(selector)[0].getContext("2d");
  	ctx.lineWidth = 2;
  	ctx.strokeStyle = "rgba(0,128,0,1)";
  	ctx.fillStyle="rgba(108,205,0,1)";
  	ctx.beginPath();
  	ctx.arc(15,15,10,0,Math.PI*2,true);
  	ctx.closePath();
  	ctx.stroke()
  	ctx.fill();
  }
}

var drawProgressBar = function(percent_free, fid) {
    var free = percent_free;
    var occupied = 100 - percent_free;
    var selector = "#indicator" + fid;
    var ctx = $(selector)[0].getContext("2d");
    ctx.lineWidth = 1;
    ctx.strokeRect(0, 5, 102, 15);
    ctx.fillStyle="rgba(108,205,0,1)";
    ctx.fillRect(1, 6, free, 13);
    ctx.fillStyle="rgba(255,0,0,1)";
    ctx.fillRect(free+1, 6, occupied, 13);
}

var convert_cell_id = function(cell, width) {
  if (isNaN(parseInt(cell))) {
    var x = width*(cell.charCodeAt(0)-65)+parseInt(cell.substring(1,cell.length),10);
    var cid = x.toString();
  } else {
    var n = parseInt(cell);
    var c = String.fromCharCode(65 + ((n - 1)/ width));
    var x = n % width || width;
    if (x < 10) 
      var cid = c + "0" + x.toString();
    else
      var cid = c + x.toString();
  }
  return cid;
}

var toggleLocation = function() {
  var locs = $('.location');
  for (var i = 0; i < locs.length; i++) {
    var loc = locs.eq(i);
    var classattr = loc.attr('class').split(' ');
    var dim = parseInt(classattr[1]);
    var total = parseInt(classattr[2]);
    var width = Math.max(dim, total/dim);
    var loclist = loc.text().split(' ');
    var cell = loclist.pop(-1);
    var cid = convert_cell_id(cell, width);
    loclist.push(cid);
    loc.text(loclist.join(' '));
  }
}

var toggleTitle = function() {
  var locs = $('.location');
  var loc = locs.eq(0);
  var classattr = loc.attr('class').split(' ');
  var dim = parseInt(classattr[1]);
  var total = parseInt(classattr[2]);
  var width = Math.max(dim, total/dim);
  var tlocs = $('#boxDisplay div a');
  for (var i = 0; i < tlocs.length; i++) {
    var tloc = tlocs.eq(i);
    var loclist = tloc.attr('title').split(' ');
    var cell = loclist.pop(-1);
    var cid = convert_cell_id(cell, width);
    loclist.push(cid);
    tloc.attr('title', loclist.join(' '));
  }
}

function highlightSelected(ctx) {
  ctx.lineWidth = 5;
  ctx.strokeStyle = "rgba(255,0,0,1)";
  ctx.fillStyle="rgba(108,205,0,1)";
  ctx.beginPath();
  ctx.arc(15,15,10,0,Math.PI*2,true);
  ctx.closePath();
  ctx.stroke();
  ctx.fill();
}

function unhighlightUnselected(ctx) {
  ctx.clearRect(0, 0, 30, 30);
  ctx.lineWidth = 2;
  ctx.strokeStyle = "rgba(0,128,0,1)";
  ctx.fillStyle="rgba(108,205,0,1)";
  ctx.beginPath();
  ctx.arc(15,15,10,0,Math.PI*2,true);
  ctx.closePath();
  ctx.stroke();
  ctx.fill();
}

