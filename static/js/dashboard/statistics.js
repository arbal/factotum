function grouptype_transform(rows) {
    for (row of rows) {
        if (['Habits and practices', 'Unidentified', 'Supplemental documents'].includes(row[0])) {
            row[2] = '';
            row[3] = '';
        }
    }
    return rows
}

$('#grouptype_table').DataTable({
    "serverSide": false,
    "info": false,
    "paging": false,
    "searching": false,
    "ordering": false,
    "ajax": {
        "url": "/grouptype/stats/",
        "dataSrc": function (json) {
            return this.grouptype_transform(json.data);
        },
    },
    "columns": [{"title": "Group Type"},
        {"title": "Documents (% of total)"},
        {"title": "Extracted Chemical Records (% of total)"},
        {"title": "Curated Chemical Records (% of total)"},]
})