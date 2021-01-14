$(document).ready(function () {

    var title_height = $('#title').height();
    var scroll_height = $(window).height() - (title_height + 80);
    $('.scroll-div').css('max-height', scroll_height);

    //create static slider for each chemical card
    document.querySelectorAll(".wf-analysis").forEach(wf_analysis => {
        var chemical_pk = wf_analysis.getAttribute('data-chemical-pk');
        var lower = wf_analysis.getAttribute('data-lower-wf-analysis');
        var central = wf_analysis.getAttribute('data-central-wf-analysis');
        var upper = wf_analysis.getAttribute('data-upper-wf-analysis');
        var input_id = 'wf_slider_' + chemical_pk;
        if (central) {
            range = false;
            value = [parseFloat(central), parseFloat(central)];
        } else {
            range = true;
            value = [parseFloat(lower.length === 0 ? '0' : lower),
                parseFloat(upper.length === 0 ? '0' : upper)];
        }
        $('#' + input_id)
            .slider({
                id: "slider" + chemical_pk,
                min: 0,
                max: 1,
                step: .00001,
                ticks: [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1],
                ticks_labels: ['0', '', '', '', '', '', '', '', '', '', '1'],
                range: range,
                value: value,
                enabled: false,
                precision: 15,
                formatter: function (value) {
                    return 'Weight fraction analysis: ' + ((value[0] === value[1]) ? value[0] : value[0] + ' - ' + value[1]);
                }
            });
    })
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
    // let scripts = doc.querySelectorAll('script')
    // for (var n = 0; n < scripts.length; n++)
    //     $.getScript(scripts[n].src)
}).fail(function (jqXHR, textStatus, errorThrown) {
    $("#card-loading-text").text("Cards Failed to Load");
})
