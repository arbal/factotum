$(document).ready(function () {
    var document_table_url = JSON.parse(document.getElementById('document_table_url').textContent);

    $('#document-table').DataTable({
        serverSide: true,
        ajax: document_table_url,
        columns: [
            {
                width: "20%",
            },
            {
                width: "20%",
            },
            {
                width: "35%",
            },
            {
                width: "5%",
            },
            {
                searchable: false,
                width: "20%",
            }
        ]
    });
});

$('#document-audit-log-modal').on('show.bs.modal', function (event) {
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