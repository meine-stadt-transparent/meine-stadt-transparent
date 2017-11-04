require('isotope-layout/dist/isotope.pkgd');

$(function () {
    // init Isotope
    let $grid = $('.persons-list').isotope({
        itemSelector: '.person',
        sortBy: 'name',
        getSortData: {
            name: '.name',
            parliamentary_group: '.parliamentary-group'
        },
    });
    window.$grid = $grid;

    $("select[name=sort_by]").change(function () {
        let sort = $(this).val();
        if (sort === 'name') {
            $grid.isotope({sortBy: 'name'});
        }
        if (sort === 'party') {
            $grid.isotope({sortBy: 'parliamentary_group'});
        }
    });

    $("#filter-parliamentary-groups").find("a").click(function () {
        let filter = $(this).data("group-id");
        if (filter === 'all') {
            $grid.isotope({filter: null});
        } else {
            $grid.isotope({filter: '.parliamentary-group-' + filter});
        }
        $("#filter-parliamentary-groups").find(".active").removeClass("active");
        $(this).addClass("active")
    });
});