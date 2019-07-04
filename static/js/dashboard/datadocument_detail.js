$(document).ready(function() {

  $('[data-toggle="tooltip"]').tooltip(); 
  var title_height = $('#title').height();
  var scroll_height = $(window).height() - (title_height + 80);
  $('.scroll-div').css('max-height', scroll_height);
  });