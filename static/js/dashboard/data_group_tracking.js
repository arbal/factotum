$(document).ready(function() {
    // Setup - add a text input to each header cell
    // $('#datagroups thead tr').clone(true).appendTo('#datagroups thead');
    $('#datagroups thead tr:eq(1) th').each(function(i) {
        var isStep = $(this).hasClass("search-curation-step");
        if (isStep) {
            $("select", this).change(function() {
                // search by whole word
                var searchTerm = $(this).children("option:selected").val();
                var regex = '\\b' + searchTerm + '\\b';
                if (table.column(i).search() !== this.searchTerm) {
                    table.column(i).search(regex, true, false).draw();
                }
            });
        } else {
            $('input', this).on('keyup change', function() {
                if (table.column(i).search() !== this.value) {
                    table.column(i).search(this.value).draw();
                }
            });
        }
    });

    var table = $('#datagroups').DataTable({
        "lengthMenu": [25, 50, 75, 100], // change number of records shown
        "order": [],
        orderCellsTop: true,
        "columnDefs": [
            {"orderable": false, "targets": [-1]}
        ]
    });
});
