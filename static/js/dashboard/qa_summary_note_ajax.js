import ajax_form_request from '../modules/ajax_form_submission.js'
// Save notes on submit with AJAX posting
$('#qa-summary-note-form').on('submit', function (event) {
    event.preventDefault();

    ajax_form_request('#qa-summary-note-form').done(function (result) {
        $("#results").text(result.result);
        $("#results").fadeIn().delay(5000).fadeOut();
    })
});
