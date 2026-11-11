// app.js

document.addEventListener('DOMContentLoaded', () => {
    // --- ESTADO DEL CARRITO ---
    let cart = [];

    // --- 1. LÓGICA DE MODALES (CARRITO Y LOGIN) ---
    const btnCarrito = document.getElementById('btn-carrito');
    const cartSidebar = document.getElementById('cart-sidebar');
    const cartOverlay = document.getElementById('cart-overlay');
    const btnCloseCart = document.getElementById('btn-close-cart');
    const cartItemsContainer = document.getElementById('cart-items');
    const cartTotalPrice = document.getElementById('cart-total-price');
    const cartCounter = document.getElementById('cart-counter');

    const btnLogin = document.getElementById('btn-login');
    const loginModal = document.getElementById('login-modal');
    const loginOverlay = document.getElementById('login-overlay');
    const btnCloseLogin = document.getElementById('btn-close-login');

    // Funciones Carrito
    function toggleCart() {
        cartSidebar.classList.toggle('translate-x-full'); 
        cartOverlay.classList.toggle('hidden'); 
    }

    if (btnCarrito) btnCarrito.addEventListener('click', toggleCart);
    if (btnCloseCart) btnCloseCart.addEventListener('click', toggleCart);
    if (cartOverlay) cartOverlay.addEventListener('click', toggleCart);

    // Funciones Login
    function toggleLogin() {
        loginModal.classList.toggle('hidden');
    }

    if (btnLogin) btnLogin.addEventListener('click', toggleLogin);
    if (btnCloseLogin) btnCloseLogin.addEventListener('click', toggleLogin);
    if (loginOverlay) loginOverlay.addEventListener('click', toggleLogin);


    // --- 2. LÓGICA DE NAVEGACIÓN POR URL ---
    const mainContent = document.getElementById('main-content');
    const dynamicContent = document.getElementById('dynamic-content');
    const dynamicTitle = document.getElementById('dynamic-title');
    const navLinks = document.querySelectorAll('.nav-link');

    function renderSection() {
        const params = new URLSearchParams(window.location.search);
        const seccion = params.get('seccion');

        if (!seccion || seccion === 'inicio') {
            if (mainContent) mainContent.classList.remove('hidden');
            if (dynamicContent) dynamicContent.classList.add('hidden');
        } else {
            if (mainContent) mainContent.classList.add('hidden');
            if (dynamicContent) dynamicContent.classList.remove('hidden');
            if (dynamicTitle) {
                dynamicTitle.innerText = seccion.replace(/-/g, ' ').toUpperCase(); 
            }
        }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault(); 
            const seccionDeseada = link.getAttribute('data-seccion');
            
            const params = new URLSearchParams(window.location.search);
            params.set('seccion', seccionDeseada);
            
            const nuevaUrl = `${window.location.pathname}?${params.toString()}`;
            window.history.pushState({ path: nuevaUrl }, '', nuevaUrl);
            
            renderSection();
            
            if (!cartSidebar.classList.contains('translate-x-full')) {
                toggleCart();
            }
        });
    });


    // --- 3. LÓGICA DEL CARRITO DINÁMICO (+ / -) ---

    // Leer carrito de la URL al inicio
    function loadCartFromURL() {
        const params = new URLSearchParams(window.location.search);
        const cartData = params.get('carrito');
        if (cartData) {
            try {
                cart = JSON.parse(decodeURIComponent(cartData));
            } catch (e) {
                console.error("Error leyendo carrito", e);
                cart = [];
            }
        }
        renderCart();
    }

    // Guardar carrito en la URL sin recargar
    function saveCartToURL() {
        const params = new URLSearchParams(window.location.search);
        if (cart.length > 0) {
            params.set('carrito', encodeURIComponent(JSON.stringify(cart)));
        } else {
            params.delete('carrito');
        }
        const nuevaUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        window.history.pushState({ path: nuevaUrl }, '', nuevaUrl);
    }

    // Funciones globales expuestas para los botones en el HTML generado
    window.addItem = function(id, name, price) {
        const item = cart.find(i => i.id === id);
        if (item) {
            item.quantity++;
        } else {
            cart.push({ id, name, price: parseInt(price), quantity: 1 });
        }
        saveCartToURL();
        renderCart();
    };

    window.removeItem = function(id) {
        const index = cart.findIndex(i => i.id === id);
        if (index !== -1) {
            cart[index].quantity--;
            if (cart[index].quantity <= 0) {
                cart.splice(index, 1);
            }
            saveCartToURL();
            renderCart();
        }
    };

    // Renderizar los items del carrito en el sidebar
    function renderCart() {
        cartItemsContainer.innerHTML = '';
        let total = 0;
        let count = 0;

        if (cart.length === 0) {
            cartItemsContainer.innerHTML = '<p class="text-center text-gray-500 mt-4">El carrito está vacío</p>';
        } else {
            cart.forEach(item => {
                total += item.price * item.quantity;
                count += item.quantity;

                const itemDiv = document.createElement('div');
                itemDiv.className = 'border-b border-gray-300 pb-4 mb-2 flex flex-col gap-2';
                
                // Diseño similar a la imagen de referencia[cite: 12]
                itemDiv.innerHTML = `
                    <div class="flex justify-between items-center w-full">
                        <span class="font-semibold">${item.name}</span>
                        <span class="text-gray-300 border-b-2 border-dotted border-gray-300 flex-grow mx-3 relative top-2"></span>
                        <span class="font-bold text-marron">$${(item.price * item.quantity).toLocaleString('es-CL')}</span>
                    </div>
                    <div class="flex justify-between items-center text-sm w-full">
                        <span class="text-gray-500">$${item.price.toLocaleString('es-CL')} c/u</span>
                        <div class="flex items-center gap-3 bg-gray-200 rounded-lg px-2 py-1">
                            <button onclick="removeItem('${item.id}')" class="text-marron hover:text-naranja font-bold px-1 transition">-</button>
                            <span class="font-bold w-4 text-center">${item.quantity}</span>
                            <button onclick="addItem('${item.id}', '${item.name}', ${item.price})" class="text-marron hover:text-naranja font-bold px-1 transition">+</button>
                        </div>
                    </div>
                `;
                cartItemsContainer.appendChild(itemDiv);
            });
        }

        cartTotalPrice.innerText = `$${total.toLocaleString('es-CL')}`;
        cartCounter.innerText = count;
        
        // Si el total es 0, ocultar el badge contador
        if(count > 0){
             cartCounter.classList.remove('hidden');
        } else {
             cartCounter.classList.add('hidden');
        }
    }

    // Escuchar clics en los botones "Agregar" de los productos principales
    const btnAgregarList = document.querySelectorAll('.btn-agregar-carrito');
    btnAgregarList.forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-id');
            const name = btn.getAttribute('data-name');
            const price = btn.getAttribute('data-price');
            
            window.addItem(id, name, price);
            
            // Abre el carrito para mostrar el producto añadido
            if (cartSidebar.classList.contains('translate-x-full')) {
                toggleCart();
            }
        });
    });

    // Escuchar botones Atrás/Adelante del navegador
    window.addEventListener('popstate', () => {
        renderSection();
        loadCartFromURL();
    });

    // Inicializar la vista
    renderSection();
    loadCartFromURL();
});


// ============================================================================
// INTEGRACIÓN CON BACKEND SEGURO EN LOCALHOST (API GATEWAY: http://localhost:8000)
// ============================================================================
const API_GATEWAY_URL = "http://localhost:8000/api/v1";
window.nikkeiSession = {
    accessToken: localStorage.getItem("nikkei_token") || null,
    usuario: JSON.parse(localStorage.getItem("nikkei_user") || "null")
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. Conectar el formulario del Modal de Login con POST /api/v1/auth/login (S06)
    const loginForm = document.querySelector('#login-modal form');
    const loginBtn = loginForm ? loginForm.querySelector('button') : null;
    const headerLoginBtn = document.getElementById('btn-login');

    function actualizarBotonPerfilUI() {
        if (window.nikkeiSession.usuario && headerLoginBtn) {
            headerLoginBtn.innerHTML = `<i class="fa-solid fa-user-check"></i> <span class="hidden md:inline-block">${window.nikkeiSession.usuario.nombreCompleto} (${window.nikkeiSession.usuario.rol})</span>`;
        }
    }
    actualizarBotonPerfilUI();

    if (loginBtn && loginForm) {
        loginBtn.addEventListener('click', async () => {
            const inputs = loginForm.querySelectorAll('input');
            const correo = inputs[0]?.value?.trim() || "camila.soto@correo.cl";
            const password = inputs[1]?.value?.trim() || "1234";

            try {
                const res = await fetch(`${API_GATEWAY_URL}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ correo, password })
                });
                const data = await res.json();
                if (!res.ok) {
                    alert(`Error de autenticación (${res.status}): ${data.detail || 'Credenciales incorrectas'}`);
                    return;
                }
                window.nikkeiSession.accessToken = data.accessToken;
                window.nikkeiSession.usuario = data.usuario;
                localStorage.setItem("nikkei_token", data.accessToken);
                localStorage.setItem("nikkei_user", JSON.stringify(data.usuario));
                actualizarBotonPerfilUI();
                document.getElementById('login-modal').classList.add('hidden');
                alert(`¡Bienvenido/a ${data.usuario.nombreCompleto}! Sesión iniciada con éxito.`);
                cargarSeguimientoPedidoActivo();
            } catch (err) {
                alert("No se pudo conectar con el API Gateway en http://localhost:8000. Asegúrate de haber iniciado el backend.");
            }
        });
    }

    // 2. Conectar botón "Ir a Pagar" del Carrito con POST /api/v1/orders (S09) y POST /api/v1/payments/initiate (S10)
    const btnPagar = document.querySelector('#cart-sidebar Footer button, #cart-sidebar div.p-6.bg-gray-200 button');
    if (btnPagar) {
        btnPagar.addEventListener('click', async () => {
            const params = new URLSearchParams(window.location.search);
            const cartRaw = params.get('carrito');
            const currentCart = cartRaw ? JSON.parse(decodeURIComponent(cartRaw)) : [];

            if (!currentCart.length) {
                alert("Tu carrito está vacío. Agrega al menos un roll antes de pagar.");
                return;
            }
            if (!window.nikkeiSession.accessToken) {
                alert("Debes iniciar sesión en 'Perfil / Login' antes de confirmar tu pedido (Prueba con: camila.soto@correo.cl / 1234).");
                document.getElementById('login-modal').classList.remove('hidden');
                return;
            }

            try {
                // Solo enviamos IDs y cantidades; el servidor calcula el precio real
                const items = currentCart.map(i => ({ productId: i.id, cantidad: i.quantity }));
                const orderRes = await fetch(`${API_GATEWAY_URL}/orders`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${window.nikkeiSession.accessToken}`,
                        'Idempotency-Key': `ord-${Date.now()}`
                    },
                    body: JSON.stringify({
                        direccionEntrega: "Av. Pajaritos 2450, Maipú",
                        items: items,
                        notas: "Pedido desde Frontend Web Nikkei Roll"
                    })
                });
                const orderData = await orderRes.json();
                if (!orderRes.ok) {
                    alert(`No se pudo crear el pedido (${orderRes.status}): ${orderData.detail}`);
                    return;
                }

                // Iniciar pago por el total oficial calculado por el servidor
                const payRes = await fetch(`${API_GATEWAY_URL}/payments/initiate`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${window.nikkeiSession.accessToken}`
                    },
                    body: JSON.stringify({
                        orderId: orderData.orderId,
                        medioPago: "SERVIPAG"
                    })
                });
                const payData = await payRes.json();
                alert(
                    `¡Pedido creado y validado por el Backend!
` +
                    `• Orden ID: ${orderData.orderId}
` +
                    `• Total Oficial Calculado en Servidor: $${orderData.totalServidor.toLocaleString('es-CL')}
` +
                    `• Transacción Pago: ${payData.paymentId} (${payData.estadoPago})`
                );
                cargarSeguimientoPedidoActivo(orderData.orderId);
            } catch (err) {
                alert("Error comunicándose con el API Gateway en http://localhost:8000.");
            }
        });
    }

    // 3. Actualizar el Widget de Seguimiento de Pedido desde el Backend (S11)
    async function cargarSeguimientoPedidoActivo(orderId = "ORD-2026-1045") {
        if (!window.nikkeiSession.accessToken) return;
        try {
            const res = await fetch(`${API_GATEWAY_URL}/orders/${orderId}`, {
                headers: { 'Authorization': `Bearer ${window.nikkeiSession.accessToken}` }
            });
            if (!res.ok) return;
            const ord = await res.json();
            const labelEstado = document.querySelector('aside p.font-bold.text-lg.text-naranja');
            if (labelEstado) {
                labelEstado.innerText = `${ord.estado} (${ord.orderId} - $${ord.totalServidor.toLocaleString('es-CL')})`;
            }
        } catch (e) {
            console.warn("Seguimiento aún no disponible:", e);
        }
    }

    if (window.nikkeiSession.accessToken) {
        cargarSeguimientoPedidoActivo();
    }
});
