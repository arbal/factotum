import csrf_ajax from '../modules/csrf_ajax.js'
import ajax_form_request from "../modules/ajax_form_submission.js";

var rows = JSON.parse(document.getElementById('tabledata').textContent);
var categories = JSON.parse(document.getElementById('categorydata').textContent);


class CategoryCellEditor {

    // gets called once after the editor is created
    init(params) {
        this.container = document.createElement('div');
        this._createTable(params);
        this._registerApplyListener();
        this.params = params;
    }

    // Return the DOM element of your editor,
    // this is what the grid puts into the DOM
    getGui() {
        return this.container;
    }

    // Gets called once by grid after editing is finished
    // if your editor needs to do any cleanup, do it here
    destroy() {
        this.applyButton.removeEventListener('click', this._applyValues);
    }

    // Gets called once after GUI is attached to DOM.
    // Useful if you want to focus or highlight a component
    afterGuiAttached() {
        this.container.focus();
    }

    // Should return the final value to the grid, the result of the editing
    getValue() {
        return this.inputValue.value;
    }

    // Gets called once after initialised.
    // If you return true, the editor will appear in a popup
    isPopup() {
        return true;
    }

    _createTable(params) {
        this.container.innerHTML = `
      <div>
        <select id="category_id" name="category_id" class="form-control-sm"></select>
        <input type="hidden" id="inputValue" name="inputValue"> 
        <button id="applyBtn" class="btn btn-sm btn-primary">Update</button>
      </div>
    `;

        this.categoryDropdown = this.container.querySelector('#category_id');
        for (let i = 0; i < categories.length; i++) {
            const option = document.createElement('option');
            option.setAttribute('value', categories[i].id);
            option.innerText = categories[i].title;
            if (params.value === categories[i].title) {
                option.setAttribute('selected', 'selected');
            }
            this.categoryDropdown.appendChild(option);
        }
        this.inputValue = this.container.querySelector('#inputValue');
        this.inputValue.value = params.value;
    }

    _registerApplyListener() {
        this.applyButton = this.container.querySelector('#applyBtn');
        this.applyButton.addEventListener('click', this._applyValues);
    }

    _applyValues = () => {
        let newData = {...this.params.data};
        let selectedcategory = categories.filter(c => c.id == this.categoryDropdown.value)[0];
        newData.newcategory = selectedcategory.id
        newData.categorytitle = selectedcategory.title;
        this.params.stopEditing();
        this.params.node.setData(newData);

        $.ajax({
            type: "POST",
            data: {
                json: JSON.stringify(newData)
            }
        }).done(function (data) {
            $("#results").text(data.message).fadeIn().delay(1000).fadeOut();
        });
    }
}

class CategoryCellRenderer {
    init(params) {
        this.gui = document.createElement('span');
        if (this._isNotNil(params.value)
            && (this._isNumber(params.value) || this._isNotEmptyString(params.value))) {
            this.gui.innerText = params.value;
        } else {
            this.gui.innerText = '';
        }
    }

    _isNotNil(value) {
        return value !== undefined && value !== null;
    }

    _isNotEmptyString(value) {
        return typeof value === 'string' && value !== '';
    }

    _isNumber(value) {
        return !Number.isNaN(Number.parseFloat(value)) && Number.isFinite(value);
    }

    getGui() {
        return this.gui;
    }
}

var columnDefs = [
    {headerName: "Reported Functional Use", field: "report_funcuse", cellEditor: CategoryCellEditor,},
    {
        headerName: "Harmonized Category",
        field: "categorytitle",
        editable: true,
        cellEditor: CategoryCellEditor,
        cellRenderer: CategoryCellRenderer
    },
    {
        headerName: "Chemical Entries", field: "fu_count", cellRenderer: params => {
            return `<a href="/functional_use_curation/${params.data.pk}/" target="_blank"> ${params.data.fu_count} </a>`
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
    singleClickEdit: true,
    columnDefs: columnDefs,
    rowData: rows,
    rowHeight: 36,
    domLayout: 'normal',
    pagination: true,
    paginationPageSize: 50,
    onGridReady: function (params) {
        params.api.sizeColumnsToFit();

        window.addEventListener('resize', function () {
            setTimeout(function () {
                params.api.sizeColumnsToFit();
            });
        });
    },
};

$('#filter-reset-button').click(function () {
    $('#filter-text-box').val('');
    gridOptions.api.setQuickFilter('');
    gridOptions.api.setFilterModel(null);
})

$('#filter-text-box').change(function () {
    gridOptions.api.setQuickFilter(document.getElementById('filter-text-box').value);
});

$('#page-size').change(function (evt) {
    var value = evt.target.value;
    if (value == "All") {
        value = gridOptions.api.paginationGetRowCount()
    }
    gridOptions.api.paginationSetPageSize(Number(value));
});

// setup the grid after the page has finished loading
document.addEventListener('DOMContentLoaded', function () {
    var gridDiv = document.querySelector('#dataGrid');
    new agGrid.Grid(gridDiv, gridOptions);
});

