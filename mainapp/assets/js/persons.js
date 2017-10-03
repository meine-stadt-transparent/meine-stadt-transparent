require('isotope-layout/dist/isotope.pkgd');

console.log("Isotope");

$(function () {
    console.log("Isotope2");

    // init Isotope
    let $grid = $('.persons-list').isotope({
        itemSelector: '.person',
        layoutMode: 'fitRows',
        getSortData: {
            name: '.name',
            party: '.party'
        }
    });

    $("select[name=sort_by]").change(function() {
        let sort = $(this).val();
        if (sort === 'name') {
            $grid.isotope({ sortBy: 'name' });
        }
        if (sort === 'party') {
            $grid.isotope({ sortBy: 'party' });
        }
    });
});