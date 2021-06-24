hasCompCheckbox = $("#id_has_composition_data")
function toggleFields(input) {
    let checked = input.checked
    $("#id_raw_min_comp")[0].disabled = !checked
    $('#id_raw_central_comp')[0].disabled = !checked
    $('#id_raw_max_comp')[0].disabled = !checked
    $('#id_unit_type')[0].disabled = !checked
}
hasCompCheckbox.click(e => {toggleFields(e.target)})
toggleFields(hasCompCheckbox[0])