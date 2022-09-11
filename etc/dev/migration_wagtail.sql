UPDATE `wagtailcore_page`
SET `latest_revision_id` = (SELECT U0.`id`
                            FROM `wagtailcore_revision` U0
                            WHERE (U0.`content_type_id` = (`wagtailcore_page`.`content_type_id`) AND
                                   U0.`object_id` = (CAST(`wagtailcore_page`.`id` AS char)))
                            ORDER BY U0.`created_at` DESC, U0.`id` DESC
    LIMIT 1)
