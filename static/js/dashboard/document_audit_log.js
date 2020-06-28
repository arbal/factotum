$(document).ready(function () {
    var table_url = JSON.parse(document.getElementById('table_url').textContent);
    $('#audit-log').DataTable({
        serverSide: true,
        paging: true,
        searching: false,
        ordering: false,
        ajax:  table_url,
    });
});
