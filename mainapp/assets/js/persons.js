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

    $grid.css("min-height", $grid.height() + "px");

    let $sortSelector = $(".sort-selector");
    $sortSelector.find("a").click((ev) => {
        ev.preventDefault();
        let $selectedNode = $(ev.currentTarget),
            sort = $selectedNode.data("sort");
        $sortSelector.find(".current-mode").text($selectedNode.text());
        if (sort === 'name') {
            $grid.isotope({sortBy: 'name'});
        }
        if (sort === 'party') {
            $grid.isotope({sortBy: 'parliamentary_group'});
        }
    });

    let $parliamentaryGroups = $(".filter-parliamentary-groups input[type=radio]");
    $parliamentaryGroups.change(() => {
        let $selected = $parliamentaryGroups.filter(":checked"),
            filter = $selected.val();
        if (filter === 'all') {
            $grid.isotope({filter: null});
        } else {
            $grid.isotope({filter: '.parliamentary-group-' + filter});
        }
    });
});