$(document).ready(function() {
    $("#search_chem_form").submit(function(event) {
        event.preventDefault();
        build_curated_chemicals_table();
    });

    function build_curated_chemicals_table() {
        return $('#curated_chemicals').dataTable({
            order: [[1, "asc"]],
            processing: true,
            serverSide: true,
            stateSave: true,
            destroy: true,
            columnDefs: [
                {
                    targets: -1,
                    data: null,
                    title: 'Action',
                    searchable: false,
                    orderable: false,
                    wrap: true,
                    "render": function() {
                        return `<div class="btn-group">
                                    <button type="button" data-toggle="modal" data-target="#confirm-modal" 
                                    class="btn btn-warning delete-linkage-btn">Remove linkage</button>
                               </div>
                        `;
                    }
                },
            ],
            ajax: {
                url: "/curated_chem_json/",
                data: function(d) {
                    d.q = $('#search_chem_text').val();
                }
            },
        });
    }

    // fill in form data from button row
    $('#curated_chemicals tbody').on('click', '.delete-linkage-btn', function() {
        let table = $('#curated_chemicals').DataTable();
        let data = table.row($(this).parents('tr')).data();
        let sid = data[0];
        let raw_chem_name = data[1];
        let raw_cas = data[2];
        $("#confirm-message").text("Are you sure to delete the linkage between " + raw_chem_name + "/" + raw_cas + " and " + sid + "?");
        $("#id_raw_chem_name").val(raw_chem_name);
        $("#id_raw_cas").val(raw_cas);
        $("#id_sid").val(sid);
    });

});