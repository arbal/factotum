$(document).ready(function () {
    var oTable = $('#duplicate-chemicals').dataTable({
        order: [[0, "asc"]],
        processing: true,
        serverSide: true,
        stateSave: true,
        ajax: "/duplicate_chemicals_json/",
    });
});