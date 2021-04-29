$(document).ready( function () {
    $('#tagset_table').DataTable({
        ajax:  window.location.href + "tagsets/",
    });
    $('#document_table').DataTable({
        columnDefs: [
            {
                name: 'data_document.title',
                orderable: true,
                searchable: true,
                targets: [0]
            },
            {
                name: 'tags',
                orderable: false,
                searchable: false,
                targets: [1]
            }
        ],
        searching: false,
        processing: true,
        serverSide: true,
        ajax:  window.location.href + "documents/",
    });
} );
