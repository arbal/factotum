$(document).ready(function () {
    document.querySelectorAll(".puc-link").forEach(puc => {
        var gen_cat = puc.getAttribute('data-gen-cat');
        puc.style.backgroundColor = pucColors.get(gen_cat)
    });
    document.querySelectorAll(".puc-nav-title").forEach(title => {
        title.addEventListener('click', event => {
            var puc_id = title.getAttribute('data-puc-id');
            console.log(puc_id)
        })

    });
});