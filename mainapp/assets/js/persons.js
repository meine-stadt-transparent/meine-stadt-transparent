import Shuffle from "shufflejs/src/shuffle";

$(function () {
    let $gridEl = $('.persons-list'),
        sortByName = (el) => {
            return el.getAttribute('data-name').toLowerCase();
        },
        sortByGroup = (el) => {
            return el.getAttribute('data-group-names').toLowerCase();
        },
        grid = new Shuffle($gridEl, {
            itemSelector: 'li.person',
            isCentered: false,
            initialSort: {by: sortByName}
        });

    $gridEl.css("min-height", $gridEl.height() + "px");

    let $sortSelector = $(".sort-selector");
    $sortSelector.find("a").click((ev) => {
        ev.preventDefault();
        let $selectedNode = $(ev.currentTarget),
            sort = $selectedNode.data("sort");
        $sortSelector.find(".current-mode").text($selectedNode.text());
        if (sort === 'name') {
            grid.sort({by: sortByName});
        }
        if (sort === 'group') {
            grid.sort({by: sortByGroup});
        }
    });

    // Unfortunately, shuffle.js apparently has no function to query the new order (to my knowledge),
    // So we have to calculate it using the new position of the items
    let getSortedItems = () => {
        let items = [];
        $gridEl.find(".person").each((i, el) => {
            let $item = $(el);
            if ($item.hasClass("shuffle-item--visible")) {
                items.push($(el));
            }
        });
        return items.sort(($it1, $it2) => {
            let pos1 = $it1.position(),
                pos2 = $it2.position();
            if (pos1.top !== pos2.top) {
                return pos1.top - pos2.top;
            } else if (pos1.left !== pos2.left) {
                return pos1.left - pos2.left;
            } else {
                return 0;
            }
        });
    };



    // Make the items tabbable in the correct order, without breaking the natural tab order of the page
    let recalcTabindexes = () => {
        let lastTabindex = 1;

        let overrideTabindex = ($el) => {
            if ($el.data('original-tabindex') === undefined) {
                let origTabindex = $el.attr('tabindex');
                $el.data('original-tabindex', (origTabindex === undefined ? 0 : origTabindex));
            }
            $el.attr('tabindex', lastTabindex);
            lastTabindex++;
        };

        // Try to find all selectable elements that appear _after_ this grid and set the tabindex explicitly
        $gridEl.parents().prevAll().find("a, input, button, [tabindex]").filter(":visible:not(:disabled)").each((i, el) => overrideTabindex($(el)));

        getSortedItems().forEach(($item) => {
            $item.find("a").attr("tabindex", lastTabindex);
            lastTabindex++;
        });

        // Try to find all selectable elements that appear _after_ this grid and set the tabindex explicitly
        $gridEl.parents().nextAll().find("a, input, button, [tabindex]").filter(":visible:not(:disabled)").each((i, el) => overrideTabindex($(el)));
    };
    grid.on(Shuffle.EventType.LAYOUT, () => {
        recalcTabindexes();
    });
    recalcTabindexes();

    if ($gridEl.parents(".tab-pane").length > 0) {
        // We're inside a tab content, so the list might disappear and reappear
        let tabId = $gridEl.parents(".tab-pane").attr("id"),
            $tab = $(".nav-link[href=\"#" + tabId + "\"]");
        $tab.on("shown.bs.tab hidden.bs.tab", () => {
            recalcTabindexes();
        });
    }

    let $groupRadios = $(".filter-organizations input[type=radio]"),
        $groupDropdownLinks = $(".filter-organizations a"),
        $currentFilterLabel = $(".filter-organizations .current-mode");

    // Update Isotope, set the label on the drop-down menu and the state of the radio-button-group
    let setParliamentaryGroup = (group) => {
        if (group === 'all') {
            grid.filter(null);
        } else {
            grid.filter('organization-' + group);
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


    /* Functions used by frontend testing to query the grid */

    // Returns the current filtered, sorted items
    $gridEl.data("get-items", () => {
        return getSortedItems();
    });
    // Given a name of a person, this function returns the position in the list of the corresponding item
    // Returns null if no person exists with that name of the person is currently not visible
    $gridEl.data("get-item-pos-by-name", (name) => {
        let positions = $gridEl.data("get-items")();
        for (let i = 0; i < positions.length; i++) {
            if (positions[i].data("name") === name) {
                return i;
            }
        }
        return null;
    });
});