$(document).ready(function () {
    $('#id_chems').change(function () {
        if (this.value) {
            $('#keyword-save').attr('disabled', false)
        } else {
            $('#keyword-save').attr('disabled', true)
        }
    })
});

$('#chemical-add-modal').on('show.bs.modal', function (event) {
    var modal = $(this);
    $.ajax({
        url: modal.attr('data-url'),
        context: document.body
    }).done(function (response) {
        modal.html(response);
    });
});

$('#chemical-update-modal').on('show.bs.modal', function (event) {
    var modal = $(this);
    var chem_pk = event.relatedTarget.value;
    $.ajax({
        url: modal.attr('data-url').replace(/47/, chem_pk.toString()),
        context: document.body
    }).done(function (response) {
        modal.html(response);
    });
});

$('#chemical-audit-log-modal').on('show.bs.modal', function (event) {
    var modal = $(this);
    $.ajax({
        url: event.relatedTarget.href,
        context: document.body,
        error: function (response) {
            alert(response.responseText);
        }

    }).done(function (response) {
        modal.html(response);
    });
});

$('[id^=chem-click-]').click(function (e) {
    // add outline to card and add/remove chemicalID to value string in input
    var inputs = $("#id_chems")[0];
    var chemList = inputs.value.split(",");
    chemList = chemList.filter(function (entry) {
        return /\S/.test(entry);
    });
    var chemId = $(this).attr("data-chem-id");
    var index = $.inArray(chemId, chemList);
    if (index == -1) {
        select_chemcard(this)
        chemList.push(chemId);
    } else {
        deselect_chemcard(this)
        chemList.splice(index, 1);
    }
    $('#selected').text(chemList.length);
    $(inputs).attr("value", chemList.join(","));
    // with no chems selected, the save buton should be disabled
    $("#id_chems").trigger('change');
})

$('#select-all-chems').click(function (e) {
    var titulo = $(this).attr("data-original-title")
    var chemList = [];
    var inputs = $("#id_chems")[0];
    if (titulo === "Select All Chemicals") {
        $(this).attr("data-original-title", "Deselect All Chemicals")
        switchIcons(this);
        $('[id^=chem-click-]').each(function (i) {
            var chemId = $(this).attr("data-chem-id");
            chemList.push(chemId);
            select_chemcard(this);
        });
    } else {
        $(this).attr("data-original-title", "Select All Chemicals")
        switchIcons(this);
        $('[id^=chem-click-]').each(function (i) {
            deselect_chemcard(this);
        });
    }
    $('#selected').text(chemList.length);
    $(inputs).attr("value", chemList.join(","));
    $("#id_chems").trigger('change');
});

function switchIcons(elem) {
    $(elem).find('#select-all').toggleClass('d-none')
    $(elem).find('#select-none').toggleClass('d-none')
};

function select_chemcard(element) {
    element.classList.remove("shadow");
    element.classList.add("shadow-none");
    element.classList.add("border");
    element.classList.add("border-primary");
}

function deselect_chemcard(element) {
    element.classList.add("shadow");
    element.classList.remove("shadow-none");
    element.classList.remove("border");
    element.classList.remove("border-primary");
}
