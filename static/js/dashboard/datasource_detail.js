$(document).ready(function () {
    var table = $('#groups').DataTable({
        "lengthMenu": [25, 50, 75, 100], // change number of records shown
        "columnDefs": [
            {
                "targets": 5, // sixth column is edit/delete links
                "orderable": false
            },
        ],
        dom: "<'row'<'col-md-4 form-inline'l><'col-md-4 form-inline'f><'col-md-4'B>>" +
            "<'row'<'col-sm-12'tr>>" +
            "<'row'<'col-sm-5'i><'col-sm-7'p>>", // order the control divs
        buttons: [{
            extend: 'csv',
            className: 'btn btn-primary btn-sm',
            text: '<span class="fa fa-sm fa-file-csv"></span> Download CSV',
            title: '{{ object.title }}_Data_Groups',
            exportOptions: {
                columns: [0, 1, 2, 3, 4],
            },
        }]
    });
});
