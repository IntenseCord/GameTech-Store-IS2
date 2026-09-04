// JavaScript principal para GameTech Store
console.log('=== MAIN.JS CARGADO ===');

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== DOMContentLoaded DISPARADO ===');
    // Inicializar funcionalidades comunes
    initializeCommonFeatures();

    // Inicializar funcionalidades específicas según la página
    const currentPath = globalThis.location.pathname;
    if (currentPath === '/' || currentPath === '/index') {
        initializeHomePage();
    } else if (currentPath.startsWith('/tienda')) {
        initializeStorePage();
    } else if (currentPath.startsWith('/juego/')) {
        initializeGameDetailPage();
    }
});

/**
 * Inicializar funcionalidades comunes a todas las páginas
 */
function initializeCommonFeatures() {
    // Navbar activa
    const currentPath = globalThis.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');

    for (const link of navLinks) {
        const href = link.getAttribute('href');
        if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
            link.classList.add('active');
        }
    }

    // Inicializar carrito de compras
    initializeShoppingCart();

    // Tooltips
    const tooltipTriggerList = Array.prototype.slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Smooth scroll para enlaces internos
    for (const anchor of document.querySelectorAll('a[href^="#"]')) {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    }
}

/**
 * Inicializar funcionalidades de la página principal
 */
function initializeHomePage() {
    // Animación de fade-in para las tarjetas de características
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
            }
        }
    }, observerOptions);

    for (const card of document.querySelectorAll('.feature-card')) {
        observer.observe(card);
    }

    // Auto-rotación de productos destacados (opcional)
    rotateFeaturedProducts();
}

/**
 * Inicializar funcionalidades de la página de tienda
 */
function initializeStorePage() {
    // Los filtros ya están manejados en el template store.html

    // Inicializar carrito de compras (simulado)
    initializeShoppingCart();

    // Inicializar comparación de productos
    initializeProductComparison();
}

/**
 * Inicializar funcionalidades de la página de detalle de juego
 */
function initializeGameDetailPage() {
    // Verificador de compatibilidad ya manejado en game_detail.html

    // Inicializar galería de imágenes (si aplica)
    initializeImageGallery();

    // Inicializar reseñas (simulado)
    initializeReviews();
}

/**
 * Funcionalidad del carrito de compras (simulada)
 */
function initializeShoppingCart() {
    console.log('=== initializeShoppingCart LLAMADO ===');
    let cart = JSON.parse(localStorage.getItem('gametech_cart')) || [];

    // Actualizar contador del carrito
    updateCartCounter();

    // Manejar clics en botones "Agregar al carrito"
    document.addEventListener('click', function(e) {
        // Buscar el botón más cercano con la clase usada en templates
        let button = e.target.closest('.add-to-cart-btn, .add-to-cart');
        if (!button) return;

        // Obtener posibles atributos de datos: soportar varias convenciones
        const dataset = button.dataset || {};
        const productId = dataset.juegoId || dataset.hardwareId || dataset.productId || dataset.product_id;
        let productType = null;
        if (dataset.juegoId) {
        productType = 'game';
        } else if (dataset.hardwareId) {
        productType = 'hardware';
        } else {
        productType = dataset.productType || dataset.product_type || null;
        }
        // Si no logramos inferir, intentar heurística por ruta/atributos
        if (!productType && productId) {
            // Si el botón tiene 'data-product-type' en minúsculas
            productType = dataset.productType || dataset.product_type || null;
        }

        if (!productId) return;

        // Normalizar productId a número cuando sea posible
        const normalizedId = Number.isNaN(Number(productId)) ? productId : Number(productId);

        addToCart(normalizedId, productType || 'hardware');
    });

    function addToCart(productId, productType) {
        // Obtener CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        // Hacer petición al servidor para agregar al carrito
        const headers = {
            'Content-Type': 'application/json',
        };
        
        // Agregar CSRF token si existe
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        fetch('/carrito/agregar', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                product_id: productId,
                product_type: productType,
                quantity: 1
            })
        })
        .then(response => {
            // Si la respuesta es una redirección (no autenticado), redirigir al login
            if (response.redirected) {
                showToast('Debes iniciar sesión para agregar productos al carrito', 'warning');
                setTimeout(() => {
                    globalThis.location.href = '/login';
                }, 2000);
                return null;
            }
            return response.json();
        })
        .then(data => {
            if (data?.success) {
                updateCartCounter(data.cart_count);
                showToast(data.message, 'success');
            } else if (data) {
                showToast(data.message || 'Error al agregar al carrito', 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error al agregar al carrito. Por favor, inicia sesión.', 'danger');
        });
    }

    function updateCartCounter(count) {
        const cartCounter = document.querySelector('.cart-counter');
        if (cartCounter) {
            const cartCount = count === undefined ? cart.length : count;
            cartCounter.textContent = cartCount;
            cartCounter.style.display = cartCount > 0 ? 'inline' : 'none';
        }
    }

    function showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        setTimeout(() => {
            if (document.body.contains(toast)) {
                toast.remove();
            }
        }, 3000);
    }
}

/**
 * Funcionalidad de comparación de productos
 */
function initializeProductComparison() {
    const compareButtons = document.querySelectorAll('.compare-btn');

    for (const button of compareButtons) {
        button.addEventListener('click', function() {
        });
    }
}

/**
 * Galería de imágenes (simulada)
 */
function initializeImageGallery() {
    const galleryImages = document.querySelectorAll('.gallery-image');

    for (const img of galleryImages) {
        img.addEventListener('click', function() {
            for (const t of galleryImages) {
                t.classList.remove('active');
            }
            this.classList.add('active');
        });
    }
}


/**
 * Sistema de reseñas (simulado)
 */
function initializeReviews() {
    const reviewForm = document.querySelector('.review-form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            e.preventDefault();
            showToast('Reseña enviada correctamente', 'success');
            this.reset();
        });
    }
}

/**
 * Funciones auxiliares (simuladas)
 */
function getGameById(id) {
    // Simulación - en producción vendría de una API
    const games = [
        { id: 1, nombre: 'Cyberpunk 2077', precio: 59.99, imagen: '/static/images/cyberpunk.jpg' },
        { id: 2, nombre: 'The Witcher 3', precio: 39.99, imagen: '/static/images/witcher3.jpg' }
    ];
    return games.find(game => game.id == id);
}

function getHardwareById(id) {
    // Simulación - en producción vendría de una API
    const hardware = [
        { id: 1, modelo: 'RTX 4060', precio: 399.99, imagen: '/static/images/rtx4060.jpg' },
        { id: 2, modelo: 'Intel Core i5-12400F', precio: 199.99, imagen: '/static/images/i5-12400f.jpg' }
    ];
    return hardware.find(item => item.id == id);
}

/**
 * Rotación automática de productos destacados
 */
function rotateFeaturedProducts() {
    const featuredProducts = document.querySelectorAll('.featured-product');
    let currentIndex = 0;

    if (featuredProducts.length <= 1) return;

    setInterval(() => {
        let index = 0;
        for (const product of featuredProducts) {
            product.style.display = index === currentIndex ? 'block' : 'none';
        };

        currentIndex = (currentIndex + 1) % featuredProducts.length;
    }, 5000);
}

/**
 * Utilidades generales
 */
const GameTechUtils = {
    // Formatear precio
    formatPrice: function(price) {
        return new Intl.NumberFormat('es-ES', {
            style: 'currency',
            currency: 'USD'
        }).format(price);
    },

    // Validar email
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Debounce para búsquedas
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Hacer las utilidades disponibles globalmente
globalThis.GameTechUtils = GameTechUtils;