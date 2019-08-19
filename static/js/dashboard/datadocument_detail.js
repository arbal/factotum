$(document).ready(function () {

  $('[data-toggle]').tooltip();
  var title_height = $('#title').height();
  var scroll_height = $(window).height() - (title_height + 80);
  $('.scroll-div').css('max-height', scroll_height);
});

// add click event to bring active element into focus when many chems
$('[id^=chem-] div').click(function (e) {
  $("#scroll-nav").animate({
    scrollTop: $(".active p").offset().top - $("#scroll-nav").offset().top + $("#scroll-nav")
      .scrollTop() - 47
  });
})

// update location for the reload that happens when editing chemical
$("#chem-scrollspy").ready(function () {
  var chem = location.href.split("#").length
  if (chem > 1) {
    location.href = location.href
  }
});

