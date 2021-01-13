$(document).ready(function () {

    $('#scroll-nav').remove(); //scrollspy not currently used on qa page

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

// var request = $.get("/datadocument/" + doc.text + "/cards", function(data) {
//     let domparser = new DOMParser()
//     let doc = domparser.parseFromString(data, "text/html")
//
//     let card_count = doc.querySelectorAll("[id^=chem-click-]").length
//
//     $("#chemical-card-panel").html(doc.querySelector("#cards"))
//     $("#card-count").text(card_count)
//
//     $("#scrollspy-panel").html(doc.querySelector("#scroll-nav"))
//
//     let scripts = doc.querySelectorAll('script')
//     for (var n = 0; n < scripts.length; n++)
//         $.getScript(scripts[n].src)
// }).fail(function(jqXHR, textStatus, errorThrown) {
//     $("#card-loading-text").text("Cards Failed to Load")
// })


// Save notes on submit
$('#qa-notes-form').on('submit', function (event) {
    event.preventDefault();
    console.log('submitting qa notes form')
    console.log(
        $('#qa-notes-textarea').val()
    )
    save_qa_notes();
});


// AJAX for posting
function save_qa_notes() {
    console.log("save_qa_notes is running")
    $.ajax({
        url: $('#qa-notes-form').attr("action"), // the endpoint
        type: "POST", // http method
        data: {
            qa_note_text: $('#qa-notes-textarea').val(),
        }, // data sent with the post request

        // handle a successful response
        success: function (json) {
            console.log(json); // log the returned json to the console
        },

        // handle a non-successful response
        error: function (xhr, errmsg, err) {
            $('#results').html("<div class='alert-box alert radius' data-alert>Oops! We have encountered an error: " + errmsg +
                " <a href='#' class='close'>&times;</a></div>"); // add the error to the dom
            console.log(xhr.status + ": " + xhr.responseText); // provide a bit more info about the error to the console
        }
    });
};

// Todo: This function now contained within csrf_ajax.
// This code could be replaced with `import csrf_ajax from '../modules/csrf_ajax.js'`
$(function () {
    // This function gets cookie with a given name
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    var csrftoken = getCookie('csrftoken');

    /*
    The functions below will create a header with csrftoken
    */

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    function sameOrigin(url) {
        // test that a given url is a same-origin URL
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                // Send the token to same-origin, relative URLs only.
                // Send the token only if the method warrants CSRF protection
                // Using the CSRFToken value acquired earlier
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

});
// end csrf_ajax.js code

$('#chemical-audit-log-modal').on('show.bs.modal', function (event) {
    $('[data-toggle]').tooltip('hide');
    var modal = $(this);
    $.ajax({
        url: event.relatedTarget.href,
        context: document.body,
        error: function (response) {
            alert(response.responseText);
        }

    }).done(function (response) {
        modal.html(response);
    });
});
