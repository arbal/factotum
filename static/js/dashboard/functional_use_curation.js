var rows = JSON.parse(document.getElementById('tabledata').textContent);

var columnDefs = [
    {headerName: "Reported Functional Use", field: "report_funcuse"},
    {headerName: "Harmonized Category", field: "category__title"},
    {
        headerName: "Count", field: "fu_count", cellRenderer: params => {
            return `<a href="/functional_use_curation/${params.data.pk}/"> ${params.data.fu_count} </a>`
        }
    },
];

// let the grid know which columns and what data to use
var gridOptions = {
    defaultColDef: {
        sortable: true,
        resizable: true,
        filter: true,
        cellStyle: {'white-space': 'normal'},
    },
    columnDefs: columnDefs,
    rowData: rows,
    rowHeight: 36,
    domLayout: 'normal',
    pagination: true,
    paginationPageSize: 50,
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

