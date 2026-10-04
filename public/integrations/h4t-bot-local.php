<?php
/**
 * Plugin Name: H4T Bot — Local Preview
 * Description: Embed one H4T Bot assistant on a local WordPress site. Not a production connector.
 * Version: 0.1.0
 * Author: High4Tech
 */
if (!defined('ABSPATH')) { exit; }
add_action('admin_menu', function () {
    add_options_page('H4T Bot Local', 'H4T Bot Local', 'manage_options', 'h4t-bot-local', function () {
        if (!current_user_can('manage_options')) { return; }
        echo '<div class="wrap"><h1>H4T Bot Local Preview</h1><p>Use the assistant ID from Channels in your local H4T workspace. This plugin only renders on localhost.</p><form method="post" action="options.php">';
        settings_fields('h4t_bot_local');
        echo '<label>Assistant ID <input name="h4t_bot_local_id" value="' . esc_attr(get_option('h4t_bot_local_id', '')) . '" maxlength="32"></label>';
        submit_button(); echo '</form></div>';
    });
});
add_action('admin_init', function () {
    register_setting('h4t_bot_local', 'h4t_bot_local_id', ['sanitize_callback' => function ($value) {
        return preg_match('/^[a-f0-9]{32}$/', $value) ? $value : '';
    }]);
});
add_action('wp_footer', function () {
    $host = wp_parse_url(home_url(), PHP_URL_HOST);
    $id = get_option('h4t_bot_local_id', '');
    if (!in_array($host, ['localhost', '127.0.0.1', '::1'], true) || !preg_match('/^[a-f0-9]{32}$/', $id)) { return; }
    echo '<script src="http://127.0.0.1:5173/embed.js" data-bot-id="' . esc_attr($id) . '" defer></script>';
});
