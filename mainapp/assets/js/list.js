import List from "list.js";

export default function init_list_for_organizations() {
    let options = {
        valueNames: ['value-in-list']
    };

    let sublists = $("#organizations-list").find("> div.organizations-list-sublist").map((_, val) => {
        return new List(val, options);
    });

    $("#organizations-list-filter").keyup((event) => {
        sublists.each((_, elem) => {
            elem.search($(event.currentTarget).val());
        });
    });

    return sublists;
}
