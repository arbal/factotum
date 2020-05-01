$(document).ready( function () {
    $('#tagset_table').DataTable({
        ajax:  window.location.href + "tagsets/",
    });
    $('#document_table').DataTable({
        processing: true,
        serverSide: true,
        ordering: true,
        stateSave: true,
        ajax:  window.location.href + "documents/",
    });
} );
