$(document).ready(function() {
    let chem_table = $('#curated_chemicals').DataTable({
        processing: true,
        serverSide: true,
        stateSave: true,
        destroy: true,
        ajax: {
            url: "/curated_chem_detail_json/",
            data: function(d) {
                d.sid = $('#sid').text();
                d.raw_chem_name = $('#raw_chem_name').text();
                d.raw_cas = $('#raw_cas').text();
                d.provisional = $('#provisional_dropdown').val();
            }
        },
    });

    $('#provisional_dropdown').on('change', function() {
        chem_table.ajax.reload();
    })
});
