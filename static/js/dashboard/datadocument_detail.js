$(document).ready(function () {

  $('[data-toggle]').tooltip();
  var title_height = $('#title').height();
  var scroll_height = $(window).height() - (title_height + 80);
  $('.scroll-div').css('max-height', scroll_height);
});

$('[id^=chem-click-]').click(function (e) {
  // add click event to bring active element into focus when many chems
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

// add color to elements on hover...
$('.hover').mouseover(function () {
  $(this).removeClass("btn-outline-secondary");
  $(this).addClass("btn-" + this.name);
})

$('.hover').mouseout(function () {
  $(this).removeClass("btn-" + this.name);
  $(this).addClass("btn-outline-secondary");
})
