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
            ajax: {
                url: "/curated_chem_json/",
                data: function(d) {
                    d.q = $('#search_chem_text').val();
                }
            },
        });
    }
});