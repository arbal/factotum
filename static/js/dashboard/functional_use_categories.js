var rows = JSON.parse(document.getElementById('tabledata').textContent);

var columnDefs = [
    {headerName: "Title", field: "title",
    cellRenderer: function (params) {
            return '<a target="_blank" href="/functional_use_category/' + params.data.id + '">' + params.data.title + '</a>';
        }
    },
    {headerName: "Description", field: "description"},
];

// let the grid know which columns and what data to use
var gridOptions = {
    defaultColDef: {
        sortable: true,
        resizable: true,
        filter: true,
        wrapText: true,
        autoHeight: true,
        cellStyle: {'white-space': 'normal'},
    },
    columnDefs: columnDefs,
    rowData: rows,
    domLayout: 'autoHeight',
    pagination: true,
    paginationPageSize: 50,
    onColumnResized: function(params) {
        params.api.resetRowHeights();
    },
    onGridReady: function(params) {
        params.api.sizeColumnsToFit();

        window.addEventListener('resize', function() {
            setTimeout(function() {
                params.api.sizeColumnsToFit();
            });
        });
    },
};

// clear all filters
function clearFilters() {
    // clear search box
    $('#filter-text-box').val('');
    gridOptions.api.setQuickFilter('');
    // clear column filter
    gridOptions.api.setFilterModel(null);
}

// filter search box
function onFilterTextBoxChanged() {
    gridOptions.api.setQuickFilter(document.getElementById('filter-text-box').value);
}

// page size changed
document.getElementById("page-size").onchange = function(evt) {
    var value = evt.target.value;
    if (value == "All") {
        value = gridOptions.api.paginationGetRowCount()
    }
    gridOptions.api.paginationSetPageSize(Number(value));
};

// setup the grid after the page has finished loading
document.addEventListener('DOMContentLoaded', function() {
    var gridDiv = document.querySelector('#dataGrid');
    new agGrid.Grid(gridDiv, gridOptions);
});

