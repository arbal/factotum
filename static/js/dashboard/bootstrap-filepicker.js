// Bootstrap 4's custom file input box doesn't change the filename
// when a file is chosen. This does that.

function setFileName(i, el) {
    if (el.files.length > 1) {
        $(el).next('.custom-file-label').text(el.files.length + " files chosen");
    } else if (el.files.length == 1) {
        var fileName = $(el).val().replace(/^.*[\\\/]/, '');
        $(el).next('.custom-file-label').text(fileName);
    }
}

$(document).ready(function () {
    $('.custom-file-input')
        .each(setFileName)
        .on('change', function (event) { setFileName(0, event.target) });
});