$(document).ready(function () {
    let title_height = $('#title').height();
    let scroll_height = $(window).height() - (title_height + 80);
    $('.scroll-div').css('max-height', scroll_height);
});

// add click event to bring active element into focus when many chemicals
$('[id^=chem-click-]').click(function (e) {
    scrollNav = $("#scroll-nav");
    scrollNav.animate({
        scrollTop: $(".active p").offset().top - scrollNav.offset().top + scrollNav.scrollTop() - 47
    });
})

// update location for the reload that happens when editing chemical
$("#chem-scrollspy").ready(function () {
    let chem = location.href.split("#").length
    if (chem > 1) {
        location.href = location.href
    }
});

$('.hover')
    .mouseover(function () {
        $(this).removeClass("btn-outline-secondary");
        $(this).addClass("btn-" + this.name);
    })
    .mouseout(function () {
        $(this).removeClass("btn-" + this.name);
        $(this).addClass("btn-outline-secondary");
    })

let page = new URLSearchParams(window.location.search).get('page');
if (!page || isNaN(page)) page = 1;

$.get("/datadocument/" + doc.text + "/cards?page=" + page, function (data) {
    let domparser = new DOMParser();
    let card_doc = domparser.parseFromString(data, "text/html");

    let card_count = card_doc.querySelectorAll("[id^=chem-click-]").length;

    $("#card-panel").html(card_doc.querySelector("#cards"));
    $("#card-count").text(card_count);

    $("#scrollspy-panel").html(card_doc.querySelector("#scroll-nav"));

    cards_init();

    // scroll to card if #chem-card-xx in url
    if (location.hash) {
        location.href = location.hash;
    }

}).fail(function (jqXHR, textStatus, errorThrown) {
    $("#card-loading-text").text("Cards Failed to Load");
})
