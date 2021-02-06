function cards_init() {

    let chemInput = $("#id_chems")[0]

let toggle_chems = $()[0]

$(document).ready(function () {
    $('#id_chems').change(function () {
        if (this.childNodes.length) {
            $('#keyword-save').attr('disabled', false)
        } else {
            $('#keyword-save').attr('disabled', true)
        }
    })
    // });

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
        if (!this.selected) {
            select_chemcard(this)
        } else {
            deselect_chemcard(this)
        }
        $('#selected').text(chemInput.childElementCount);
        // with no chems selected, the save buton should be disabled
        $("#id_chems").trigger('change');
    })

    $('#select-all-chems').click(function (e) {
        var titulo = $(this).attr("data-original-title")
        while (chemInput.firstChild) {
            chemInput.removeChild(chemInput.lastChild);
        }
        if (titulo === "Select All Chemicals") {
            $(this).attr("data-original-title", "Deselect All Chemicals")
            switchIcons(this);
            $('[id^=chem-click-]').each(function (i) {
                select_chemcard(this);
            });
        } else {
            $(this).attr("data-original-title", "Select All Chemicals")
            switchIcons(this);
            $('[id^=chem-click-]').each(function (i) {
                deselect_chemcard(this);
            });
        }
        $('#selected').text(chemInput.childElementCount);
        $("#id_chems").trigger('change');
    });
}

function switchIcons(elem) {
    $(elem).find('#select-all').toggleClass('d-none')
    $(elem).find('#select-none').toggleClass('d-none')
}

function select_chemcard(element) {
    let chemInput = $("#id_chems")[0]
    let chemId = element.getAttribute("data-chem-id")
    let new_selection = document.createElement('option')
    new_selection.setAttribute("value", chemId)
    new_selection.setAttribute("selected", true)

    chemInput.appendChild(new_selection)

    element.selected = true;
    element.classList.remove("shadow");
    element.classList.add("shadow-none");
    element.classList.add("border");
    element.classList.add("border-primary");
}

function deselect_chemcard(element) {
    let chemInput = $("#id_chems")[0]
    let chemId = element.getAttribute("data-chem-id")
    for (child of chemInput.childNodes) {
        if (child.value === chemId) {
            chemInput.removeChild(child);
            break;
        }
    }

    element.selected = false;
    element.classList.add("shadow");
    element.classList.remove("shadow-none");
    element.classList.remove("border");
    element.classList.remove("border-primary");
}

$('#toggle-flags-modal').on('show.bs.modal', function (event) {
    $("#id_chems").clone().appendTo($('#chem_toggle_clear'))
    $("#id_chems").clone().appendTo($('#chem_toggle_detected'))
    $("#id_chems").clone().appendTo($('#chem_toggle_non_detected'))
});
