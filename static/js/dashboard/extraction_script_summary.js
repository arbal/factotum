$(document).ready(function () {
    var document_table_url = JSON.parse(document.getElementById('document_table_url').textContent);

    $('#document-table').DataTable({
        serverSide: true,
        ajax: document_table_url,
        columns: [
            {
                data: 'data_group__title',
                width: "20%",
            },
            {
                data: 'data_document__title',
                width: "20%",
            },
            {
                data: 'qanotes__qa_notes',
                width: "40%",
            },
            {
                data: 'data_document__raw_chem',
                width: "5%",
            },
            {
                data: 'last_updated',
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