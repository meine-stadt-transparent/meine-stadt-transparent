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


    let $groupRadios = $(".filter-parliamentary-groups input[type=radio]"),
        $groupDropdownLinks = $(".filter-parliamentary-groups a"),
        $currentFilterLabel = $(".filter-parliamentary-groups .current-mode");

    // Update Isotope, set the label on the drop-down menu and the state of the radio-button-group
    let setParliamentaryGroup = (group) => {
        if (group === 'all') {
            $grid.isotope({filter: null});
        } else {
            $grid.isotope({filter: '.parliamentary-group-' + group});
        }
        let name = $groupDropdownLinks.filter("[data-filter=" + group + "]").text();
        $currentFilterLabel.text(name);
        $groupRadios.filter("[value=" + group + "]:not(:checked)").prop("checked", true).trigger("click");
    };
    // Radio-Button-Group version
    $groupRadios.change(() => {
        setParliamentaryGroup($groupRadios.filter(":checked").val());
    });
    // Drop-Down version
    $groupDropdownLinks.click((ev) => {
        ev.preventDefault();
        setParliamentaryGroup($(ev.currentTarget).data("filter"));
    });
});