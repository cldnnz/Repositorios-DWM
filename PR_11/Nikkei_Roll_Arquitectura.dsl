workspace "Nikkei Roll" "Arquitectura de la implementación local entregada (Caso 19: Fukusuke Sushi-Delivery)" {
    !identifiers hierarchical
    model {
        cliente = person "Cliente" "Arma su carrito, paga y consulta sus propios pedidos"
        admin = person "Administrador" "Gestiona productos, disponibilidad y pedidos (puede anular)"
        owner = person "Dueño" "Consulta el reporte de ventas y la disponibilidad del catálogo"
        cashier = person "Cajero Virtual" "Gestiona comprobantes y consulta pedidos de la caja web"
        dispatch = person "Encargado de Despacho" "Consulta órdenes pagadas y registra el avance de entrega"
        operador = person "Operador de mensajería" "Publica y consume pedidos de cocina desde la terminal"
        sistema = softwareSystem "Nikkei Roll" "Venta online de sushi fusión peruano-japonés con carrito, pagos, despacho y reportes" {
            web = container "Frontend web" "HTML, Tailwind CSS y JavaScript. Se sirve con http.server en el puerto 3000" "HTML / CSS / JavaScript"
            gateway = container "API Gateway" "FastAPI 8000. Única entrada del navegador. Valida token, aplica roles y reenvía" "Python / FastAPI" {
                g_entrada = component "Entrada HTTP y rutas anónimas" "CORSMiddleware y rutas S01, S02 y S03 sin sesión" "Python / FastAPI"
                g_sesion = component "Proxy de sesión" "s06_login y s07_logout. Reenvía credenciales y cierre al servicio de autenticación" "Python / FastAPI"
                g_token = component "Verificación de Bearer" "verify_bearer_token. Introspección del token en cada ruta protegida" "Python / FastAPI"
                g_roles = component "Control de rol" "S13 y S16. Responde 403 si el rol no es ADMINISTRADOR o DUENO" "Python / FastAPI"
                g_reenvio = component "Reenvío privado" "forward_to_backend. Descarta cabeceras del navegador, agrega X-Gateway-Secret, identidad y X-Correlation-Id" "Python / FastAPI"
            }
            auth = container "Servicio de autenticación" "FastAPI 9000. Usuarios semilla con PBKDF2, tokens Bearer opacos de 15 minutos e introspección" "Python / FastAPI"
            core = container "Servicios de dominio" "FastAPI 9001. Inventario, clientes, pedidos y pagos. Solo acepta tráfico con X-Gateway-Secret" "Python / FastAPI" {
                c_guardia = component "Guardia del gateway" "verify_gateway. Compara X-Gateway-Secret en tiempo constante" "Python / FastAPI"
                c_catalogo = component "Catálogo e ingredientes" "inventory. S01, S02 y S13. Catálogo público, Arma tu Roll y disponibilidad" "Python / FastAPI"
                c_cobertura = component "Cobertura de reparto" "clients. S03. Verifica el radio de 3 km en Maipú" "Python / FastAPI"
                c_pedidos = component "Pedidos" "orders. S09, S11, S12 y S16. Recalcula el total, descuenta stock, Anti-BOLA, anulación y reporte" "Python / FastAPI"
                c_pagos = component "Pagos" "payments. S10. Verifica propiedad del pedido y entrega el monto oficial a cobrar" "Python / FastAPI"
                c_datos = component "Acceso a datos" "get_db e init_db. Crea el esquema y los datos semilla" "Python / sqlite3"
            }
            graphql = container "Agregador GraphQL" "Node.js 4000. Apollo Server y Mongoose. Consultas y mutaciones de productos" "Node.js / Apollo Server" {
                q_esquema = component "Esquema GraphQL" "typeDefs. Producto, ProductoInput, Query y Mutation" "Node.js / Apollo Server"
                q_resolvers = component "Resolvers" "getProductos, getProductoById, addProducto, updProducto y delProducto" "Node.js"
                q_modelo = component "Modelo Producto" "models/producto. Colección de productos en MongoDB" "Node.js / Mongoose"
            }
            broker = container "ActiveMQ" "Broker STOMP 1.2 en el puerto 61613. Cola persistente /queue/pedidos_nikkei" "ActiveMQ" {
                tags "Queue"
            }
            productor = container "Productor de pedidos" "Python. backend/messaging/productor.py. Formatos texto, fijo, JSON y XML" "Python / stomp.py"
            consumidor = container "Consumidor de cocina" "Python. backend/messaging/consumidor.py. ACK o NACK por mensaje" "Python / stomp.py"
            db = container "nikkei_roll.db" "Archivo SQLite en backend/db con productos, ingredientes, clientes, pedidos, líneas y pagos" "SQLite" {
                tags "Database"
            }
            mongo = container "nikkei_roll_db" "Base MongoDB local 27017 con la colección de productos" "MongoDB" {
                tags "Database"
            }
        }
        servipag = softwareSystem "Pasarela de pago (Servipag)" "Cobro externo del pedido. En la entrega local es un sandbox simulado" "External"

        sistema.core -> sistema.db "Lee y escribe sus datos" "SQLite local"
        sistema.graphql -> sistema.mongo "Lee y escribe productos" "Mongoose / TCP 27017"

        cliente -> sistema "Compra y consulta sus propios pedidos" "HTTP"
        cliente -> sistema.web "Compra y consulta sus propios pedidos" "HTTP"
        admin -> sistema "Gestiona productos, disponibilidad y pedidos" "HTTP"
        admin -> sistema.web "Gestiona productos, disponibilidad y pedidos" "HTTP"
        owner -> sistema "Consulta reporte de ventas y catálogo" "HTTP"
        owner -> sistema.web "Consulta reporte de ventas y catálogo" "HTTP"
        cashier -> sistema "Gestiona comprobantes de la caja web" "HTTP"
        cashier -> sistema.web "Gestiona comprobantes de la caja web" "HTTP"
        dispatch -> sistema "Consulta órdenes y registra el avance de entrega" "HTTP"
        dispatch -> sistema.web "Consulta órdenes y registra el avance de entrega" "HTTP"
        operador -> sistema "Opera la cola de pedidos de cocina" "Terminal"
        operador -> sistema.productor "Ejecuta productor.py" "Terminal"
        operador -> sistema.consumidor "Ejecuta consumidor.py" "Terminal"

        sistema.web -> sistema.gateway "Envía peticiones REST con Bearer" "HTTP / JSON"
        sistema.gateway -> sistema.auth "Login, logout e introspección del token" "HTTP + X-Gateway-Auth-Secret"
        sistema.gateway -> sistema.core "Reenvía rutas permitidas con identidad y rol" "HTTP + X-Gateway-Secret"
        sistema.gateway -> sistema.graphql "Reenviará consultas agregadas" "HTTP / GraphQL" "Planificado"

        sistema.productor -> sistema.broker "Publica el pedido en /queue/pedidos_nikkei" "STOMP 1.2"
        sistema.consumidor -> sistema.broker "Se suscribe y confirma ACK o NACK" "STOMP 1.2"
        sistema.broker -> sistema.consumidor "Entrega un pedido a la vez" "STOMP 1.2"
        sistema.core -> sistema.broker "Publicará el pedido pagado" "STOMP 1.2" "Planificado"
        sistema.core -> servipag "Creará la sesión de cobro" "HTTPS" "Planificado"
        sistema -> servipag "Cobra el pedido según configuración" "HTTPS" "Planificado"

        sistema.web -> sistema.gateway.g_entrada "Envía solicitud" "HTTP / JSON"
        sistema.gateway.g_entrada -> sistema.gateway.g_sesion "Login o logout" "Llamada interna"
        sistema.gateway.g_entrada -> sistema.gateway.g_token "Ruta protegida" "Llamada interna"
        sistema.gateway.g_entrada -> sistema.gateway.g_reenvio "Ruta anónima" "Llamada interna"
        sistema.gateway.g_sesion -> sistema.auth "Reenvía credenciales o cierre de sesión" "HTTP + X-Gateway-Auth-Secret"
        sistema.gateway.g_token -> sistema.auth "POST /introspect" "HTTP + X-Gateway-Auth-Secret"
        sistema.gateway.g_token -> sistema.gateway.g_roles "Token activo en ruta restringida" "Llamada interna"
        sistema.gateway.g_token -> sistema.gateway.g_reenvio "Token activo" "Llamada interna"
        sistema.gateway.g_roles -> sistema.gateway.g_reenvio "Rol autorizado" "Llamada interna"
        sistema.gateway.g_reenvio -> sistema.core "Enruta hacia el servicio privado" "HTTP + X-Gateway-Secret"
        sistema.gateway.g_reenvio -> sistema.web "Devuelve la respuesta con X-Correlation-Id" "HTTP / JSON"

        sistema.gateway -> sistema.core.c_guardia "Reenvía solicitud con secreto e identidad" "HTTP + X-Gateway-Secret"
        sistema.core.c_guardia -> sistema.core.c_catalogo "Solicitud autorizada" "Llamada interna"
        sistema.core.c_guardia -> sistema.core.c_cobertura "Solicitud autorizada" "Llamada interna"
        sistema.core.c_guardia -> sistema.core.c_pedidos "Solicitud autorizada" "Llamada interna"
        sistema.core.c_guardia -> sistema.core.c_pagos "Solicitud autorizada" "Llamada interna"
        sistema.core.c_pedidos -> sistema.core.c_catalogo "Valida disponibilidad, precios y descuenta stock" "Llamada interna"
        sistema.core.c_pagos -> sistema.core.c_pedidos "Consulta propietario e importe oficial" "Llamada interna"
        sistema.core.c_catalogo -> sistema.core.c_datos "Lee y actualiza productos" "Llamada interna"
        sistema.core.c_pedidos -> sistema.core.c_datos "Lee y escribe pedidos y líneas" "Llamada interna"
        sistema.core.c_pagos -> sistema.core.c_datos "Lee pedidos" "Llamada interna"
        sistema.core.c_datos -> sistema.db "Lee y escribe" "SQLite local"
        sistema.core.c_pedidos -> sistema.broker "Publicará el pedido pagado" "STOMP 1.2" "Planificado"
        sistema.core.c_pagos -> servipag "Creará la sesión de cobro" "HTTPS" "Planificado"

        sistema.gateway -> sistema.graphql.q_esquema "Reenviará la consulta GraphQL" "HTTP / GraphQL" "Planificado"
        sistema.graphql.q_esquema -> sistema.graphql.q_resolvers "Valida y ejecuta la operación" "Llamada interna"
        sistema.graphql.q_resolvers -> sistema.graphql.q_modelo "Consulta o modifica productos" "Llamada interna"
        sistema.graphql.q_modelo -> sistema.mongo "find, save y findByIdAndUpdate" "Mongoose / TCP 27017"
    }
    views {
        systemContext sistema "C1_Contexto" {
            title "C1 · Contexto de Nikkei Roll · Nikkei Roll"
            include cliente admin owner cashier dispatch operador sistema servipag
            autoLayout tb
        }
        container sistema "C2_Contenedores" {
            title "C2 · Contenedores de Nikkei Roll · Nikkei Roll"
            include sistema.web sistema.gateway sistema.auth sistema.core sistema.graphql sistema.broker sistema.productor sistema.consumidor sistema.db sistema.mongo servipag
            autoLayout tb
        }
        component sistema.gateway "C3_Gateway" {
            title "C3 · Componentes del gateway · Nikkei Roll"
            include sistema.web sistema.gateway.g_entrada sistema.gateway.g_sesion sistema.gateway.g_token sistema.gateway.g_roles sistema.gateway.g_reenvio sistema.auth sistema.core
            autoLayout tb
        }
        component sistema.core "C3_Servicios_Dominio" {
            title "C3 · Componentes de los servicios de dominio · Nikkei Roll"
            include sistema.gateway sistema.core.c_guardia sistema.core.c_catalogo sistema.core.c_cobertura sistema.core.c_pedidos sistema.core.c_pagos sistema.core.c_datos sistema.db sistema.broker servipag
            autoLayout tb
        }
        component sistema.graphql "C3_GraphQL" {
            title "C3 · Agregador GraphQL · Nikkei Roll"
            include sistema.gateway sistema.graphql.q_esquema sistema.graphql.q_resolvers sistema.graphql.q_modelo sistema.mongo
            autoLayout tb
        }
        dynamic sistema "D_Autenticacion" {
            title "Flujo · Inicio de sesión · Nikkei Roll"
            1: cliente -> sistema.web "Ingresa correo y contraseña"
            2: sistema.web -> sistema.gateway "POST /api/v1/auth/login"
            3: sistema.gateway -> sistema.auth "Reenvía credenciales. Devuelve token Bearer de 15 minutos"
            autoLayout tb
        }
        dynamic sistema "D_Registro_Pedido" {
            title "Flujo · Registro de pedido · Nikkei Roll"
            1: cliente -> sistema.web "Confirma carrito y dirección"
            2: sistema.web -> sistema.gateway "POST /api/v1/orders con Bearer"
            3: sistema.gateway -> sistema.auth "Introspecciona el token"
            4: sistema.gateway -> sistema.core "Reenvía identidad, rol y secreto interno"
            5: sistema.core -> sistema.db "Valida stock y recalcula el total con precios vigentes"
            6: sistema.core -> sistema.db "Guarda PENDIENTE_PAGO y descuenta stock"
            autoLayout tb
        }
        dynamic sistema "D_Consulta_Protegida" {
            title "Flujo · Consulta protegida de un pedido · Nikkei Roll"
            1: cliente -> sistema.web "Abre el seguimiento de su pedido"
            2: sistema.web -> sistema.gateway "GET /api/v1/orders/{id} con Bearer"
            3: sistema.gateway -> sistema.auth "Introspecciona el token"
            4: sistema.gateway -> sistema.core "Reenvía identidad y rol"
            5: sistema.core -> sistema.db "Lee el pedido y compara el dueño (Anti-BOLA)"
            autoLayout tb
        }
        dynamic sistema "D_Pago" {
            title "Flujo · Inicio de pago · Nikkei Roll"
            1: cliente -> sistema.web "Pulsa Ir a Pagar"
            2: sistema.web -> sistema.gateway "POST /api/v1/payments/initiate"
            3: sistema.gateway -> sistema.auth "Introspecciona el token"
            4: sistema.gateway -> sistema.core "Reenvía solicitud con identidad"
            5: sistema.core -> sistema.db "Comprueba propiedad y toma el monto oficial"
            autoLayout tb
        }
        dynamic sistema "D_Mensajeria_Cocina" {
            title "Flujo · Mensajería de pedidos a cocina · Nikkei Roll"
            1: operador -> sistema.consumidor "Ejecuta consumidor.py"
            2: sistema.consumidor -> sistema.broker "SUBSCRIBE con ack client-individual"
            3: operador -> sistema.productor "Ejecuta productor.py con el formato elegido"
            4: sistema.productor -> sistema.broker "SEND persistente a /queue/pedidos_nikkei"
            5: sistema.broker -> sistema.consumidor "Entrega un pedido (prefetch 1)"
            6: sistema.consumidor -> sistema.broker "ACK si es válido, NACK si no"
            autoLayout tb
        }
        styles {
            element "Person" {
                shape Person
                background #526579
                color #FFFFFF
            }
            element "Software System" {
                background #195F69
                color #FFFFFF
            }
            element "External" {
                background #667586
                color #FFFFFF
            }
            element "Container" {
                background #EDF2F7
                color #172B40
            }
            element "Database" {
                shape Cylinder
            }
            element "Queue" {
                shape Pipe
            }
            element "Component" {
                background #FFFFFF
                color #172B40
            }
            relationship "Planificado" {
                dashed true
                color #B45309
            }
        }
    }
}
