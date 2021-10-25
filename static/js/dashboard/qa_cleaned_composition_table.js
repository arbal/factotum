$(document).ready(function () {
    var cleaned_composition_table_url = JSON.parse(document.getElementById('cleaned_composition_table_url').textContent);

    $('#cleaned-composition-table').DataTable({
        serverSide: true,
        ajax: cleaned_composition_table_url,
        columns: [
            {
                width: "40%",
            },
            {
                width: "30%",
            },
            {
                width: "30%",
            },
        ]
    });
});