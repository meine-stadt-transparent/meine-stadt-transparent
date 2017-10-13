require('isotope-layout/dist/isotope.pkgd');

$(function () {
    // init Isotope
    let $grid = $('.persons-list').isotope({
        itemSelector: '.person',
        layoutMode: 'fitRows',
        getSortData: {
            name: '.name',
            parliamentary_group: '.parliamentary-group'
        }
    });
    window.$grid = $grid;

    $("select[name=sort_by]").change(function() {
        let sort = $(this).val();
        if (sort === 'name') {
            $grid.isotope({ sortBy: 'name' });
        }
        if (sort === 'party') {
            $grid.isotope({ sortBy: 'parliamentary_group' });
        }
    });
    $("input[name=parliamentary-group]").change(function() {
        let filter = $(this).val();
        if (filter === 'all') {
            $grid.isotope({ filter: null });
        } else {
            $grid.isotope({ filter: '.parliamentary-group-' + filter });
        }
        console.log(filter);
    });
});