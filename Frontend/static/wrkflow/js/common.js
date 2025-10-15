// svg icons support ie11
(function () {
    svg4everybody();
})();

// carousel arrows
const navArrows = [`
    <svg class="icon icon-arrow-prev">
        <use xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="img/sprite.svg#icon-arrow-prev"></use>
    </svg>`, `<svg class="icon icon-arrow-next">
        <use xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="img/sprite.svg#icon-arrow-next"></use>
    </svg>`];

// owl carousel
$(document).ready(function () {
    const slider = $('.js-slider-review');
    slider.owlCarousel({
        items: 1,
        nav: false,
        navElement: 'button',
        navText: navArrows,
        dots: true,
        loop: true,
        smartSpeed: 700,
        autoHeight: true
    });
});

// magnificPopup
(function () {
    var link = $('.js-popup-open');
    link.magnificPopup({
        type: 'inline',
        fixedContentPos: true,
        removalDelay: 200,
        callbacks: {
            beforeOpen: function () {
                this.st.mainClass = this.st.el.attr('data-effect');
            }
        }
    });
})();

// accord
(function () {
    const accord = $('.js-accord'),
          items = accord.find('.js-accord-item');
    items.each(function () {
        let item = $(this),
            head = item.find('.js-accord-head'),
            body = item.find('.js-accord-body');

        head.on('click', function () {
            item.toggleClass('active');
            body.slideToggle();
        });
    });
})();

// header
(function () {
    const header = $('.js-header'),
          burger = header.find('.js-header-burger'),
          wrap = header.find('.js-header-wrap'),
          html = $('html'),
          body = $('body');
    burger.on('click', function () {
        burger.toggleClass('active');
        wrap.toggleClass('visible');
        html.toggleClass('no-scroll');
        body.toggleClass('no-scroll');
    });
})();

// body toggle bg
(function () {
    const switchBody = $('.js-switch-bg'),
          body = $('body');
    switchBody.on('change', function () {
        body.toggleClass('dark');
    });
})();

// aos animation
AOS.init();

// parallax
var image = document.getElementsByClassName('js-parallax');
new simpleParallax(image, {
    scale: 1.3,
    overflow: true,
    delay: .6
});

var image = document.getElementsByClassName('js-parallax-left');
new simpleParallax(image, {
    scale: 1.4,
    overflow: true,
    delay: .6,
    orientation: 'left'
});

var image = document.getElementsByClassName('js-parallax-right');
new simpleParallax(image, {
    scale: 1.4,
    overflow: true,
    delay: .6,
    orientation: 'right'
});

// price toggle
(function () {

    const pricing = $('.js-pricing'),
          switchPricing = pricing.find('.js-pricing-switch'),
          money = pricing.find('.js-pricing-money');
    switchPricing.on('change', function () {
        money.toggleClass('active');
    });
})();