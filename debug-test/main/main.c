#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "sdkconfig.h"

#if defined(CONFIG_IDF_TARGET_ESP32S3)
#include "led_strip.h"
#endif

#if defined(CONFIG_IDF_TARGET_ESP32)
#define LED_GPIO 2
#elif defined(CONFIG_IDF_TARGET_ESP32S3)
// #define LED_GPIO 2
#define RGB_GPIO 21
#else
#define LED_GPIO 8
#endif

volatile int loop_counter = 0;

#if defined(RGB_GPIO)
static led_strip_handle_t rgb_strip;

static void rgb_init(void) {
    led_strip_config_t strip_config = {
        .strip_gpio_num = RGB_GPIO,
        .max_leds = 1,
        .led_pixel_format = LED_PIXEL_FORMAT_GRB,
        .led_model = LED_MODEL_WS2812,
        .flags = {
            .invert_out = false,
        },
    };
    led_strip_rmt_config_t rmt_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000,
        .mem_block_symbols = 64,
        .flags = {
            .with_dma = false,
        },
    };

    led_strip_new_rmt_device(&strip_config, &rmt_config, &rgb_strip);
    led_strip_clear(rgb_strip);
}

static void rgb_set(uint8_t r, uint8_t g, uint8_t b) {
    led_strip_set_pixel(rgb_strip, 0, r, g, b);
    led_strip_refresh(rgb_strip);
}
#endif

void __attribute__((noinline)) debug_loop(void) {
    loop_counter++;
    printf("LOOP: %d\n", loop_counter);

#if defined(RGB_GPIO)
    switch (loop_counter % 4) {
        case 0:
            rgb_set(32, 0, 0);
            break;
        case 1:
            rgb_set(0, 32, 0);
            break;
        case 2:
            rgb_set(0, 0, 32);
            break;
        default:
            rgb_set(0, 0, 0);
            break;
    }
#else
    gpio_set_level(LED_GPIO, loop_counter % 2);
#endif

    vTaskDelay(pdMS_TO_TICKS(500));
}

void app_main(void) {
#if defined(RGB_GPIO)
    rgb_init();
#else
    gpio_reset_pin(LED_GPIO);
    gpio_set_direction(LED_GPIO, GPIO_MODE_OUTPUT);
#endif

    printf("DEBUG_TEST_READY\n");

    while (1) {
        debug_loop();
    }
}
