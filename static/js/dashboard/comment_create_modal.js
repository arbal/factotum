import ajax_form_request from '../modules/ajax_form_submission.js'

// Submit post on submit
$('#comment-create-form').on('submit', function (event) {
    event.preventDefault();
    $('#comment-create-form #id_page_url')[0].value = location.pathname
    ajax_form_request('#comment-create-form').done(function () {
        location.reload()
    })
});
