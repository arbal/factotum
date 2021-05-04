$(document).ready(function () {

    var title_height = $('#title').height();
    var scroll_height = $(window).height() - (title_height + 80);
    $('.scroll-div').css('max-height', scroll_height);
});

$('[id^=chem-click-]').click(function (e) {
    // add click event to bring active element into focus when many chems
    scrollNav = $("#scroll-nav");
    scrollNav.animate({
        scrollTop: $(".active p").offset().top - scrollNav.offset().top + scrollNav.scrollTop() - 47
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

var request = $.get("/datadocument/" + doc.text + "/cards", function (data) {
    let domparser = new DOMParser();
    let card_doc = domparser.parseFromString(data, "text/html");

    let card_count = card_doc.querySelectorAll("[id^=chem-click-]").length;

    $("#card-panel").html(card_doc.querySelector("#cards"));
    $("#card-count").text(card_count);

    $("#scrollspy-panel").html(card_doc.querySelector("#scroll-nav"));

    cards_init();

    // scroll to card if in url
    if (location.hash) {
        location.href = location.hash;
    }
    // let scripts = doc.querySelectorAll('script')
    // for (var n = 0; n < scripts.length; n++)
    //     $.getScript(scripts[n].src)
}).fail(function (jqXHR, textStatus, errorThrown) {
    $("#card-loading-text").text("Cards Failed to Load");
})
