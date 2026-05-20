"""30 synthetic FAQ items (6 topics × 5) for the PayChat marketplace."""

FAQ_ITEMS: list[tuple[str, str, str]] = [
    # (topic, question, answer)
    # --- Reembolso ---
    (
        "reembolso",
        "Como solicito um reembolso?",
        "Para solicitar um reembolso, acesse 'Meus Pedidos', selecione o pedido e clique em "
        "'Solicitar Reembolso'. O processo é analisado em até 5 dias úteis.",
    ),
    (
        "reembolso",
        "Em quanto tempo recebo o reembolso após aprovação?",
        "Após aprovação, o crédito ocorre em 7 a 10 dias úteis no cartão ou em até 3 dias "
        "úteis para transferência bancária.",
    ),
    (
        "reembolso",
        "Posso cancelar uma solicitação de reembolso?",
        "Sim, enquanto o status for 'Em Análise'. Acesse 'Meus Pedidos' e clique em "
        "'Cancelar Solicitação'.",
    ),
    (
        "reembolso",
        "Quais pedidos são elegíveis para reembolso?",
        "Pedidos concluídos há menos de 30 dias, com status diferente de 'Reembolsado'. "
        "Produtos digitais têm política específica.",
    ),
    (
        "reembolso",
        "O reembolso cobre o valor do frete?",
        "Sim, quando o problema é do vendedor ou da plataforma. Em casos de arrependimento, "
        "o frete de retorno é por conta do comprador.",
    ),
    # --- Entrega ---
    (
        "entrega",
        "Qual é o prazo de entrega?",
        "O prazo varia por vendedor e modalidade de frete. Ele é exibido ao finalizar a compra "
        "e pode ser acompanhado em 'Meus Pedidos'.",
    ),
    (
        "entrega",
        "Como rastreio meu pedido?",
        "Após o envio, você recebe o código de rastreamento por e-mail. Insira no site da "
        "transportadora ou acompanhe em 'Meus Pedidos'.",
    ),
    (
        "entrega",
        "O que fazer se o pedido não chegar no prazo?",
        "Acesse 'Meus Pedidos', selecione o pedido e clique em 'Reportar Problema'. "
        "Nosso suporte responde em até 24 horas.",
    ),
    (
        "entrega",
        "Posso alterar o endereço de entrega após a compra?",
        "Somente enquanto o pedido estiver com status 'Aguardando Envio'. "
        "Entre em contato com o suporte imediatamente.",
    ),
    (
        "entrega",
        "O que acontece se eu não estiver em casa na entrega?",
        "A transportadora tenta por 3 dias úteis consecutivos. Depois, o pacote fica disponível "
        "para retirada por 7 dias.",
    ),
    # --- Pagamento ---
    (
        "pagamento",
        "Quais formas de pagamento são aceitas?",
        "Cartão de crédito, débito, boleto bancário e Pix. Parcelamento disponível em até 12x "
        "no cartão de crédito.",
    ),
    (
        "pagamento",
        "Meu pagamento foi recusado. O que fazer?",
        "Verifique os dados do cartão, saldo e limite. Se persistir, tente outra forma de "
        "pagamento ou contate seu banco.",
    ),
    (
        "pagamento",
        "É seguro inserir meus dados de pagamento?",
        "Sim. Utilizamos criptografia SSL e não armazenamos dados completos do cartão. "
        "Transações processadas por gateway certificado PCI-DSS.",
    ),
    (
        "pagamento",
        "Posso dividir o pagamento entre dois cartões?",
        "No momento não. É possível usar um cartão e complementar com Pix.",
    ),
    (
        "pagamento",
        "Quando o valor é cobrado no cartão?",
        "Para compras aprovadas, em até 2 dias úteis. Para boleto, após pagamento e "
        "compensação bancária.",
    ),
    # --- Cadastro ---
    (
        "cadastro",
        "Como me cadastro como vendedor?",
        "Acesse 'Quero Vender', preencha seus dados, envie CPF ou CNPJ e aguarde análise "
        "em até 2 dias úteis.",
    ),
    (
        "cadastro",
        "Posso ter conta de comprador e vendedor ao mesmo tempo?",
        "Sim. Após aprovação como vendedor, ative o modo vendedor nas configurações da conta.",
    ),
    (
        "cadastro",
        "Como altero minha senha?",
        "Acesse 'Minha Conta' > 'Segurança' > 'Alterar Senha' e confirme pelo e-mail cadastrado.",
    ),
    (
        "cadastro",
        "O que fazer se esquecer minha senha?",
        "Na tela de login, clique em 'Esqueci minha senha'. Enviaremos link de redefinição "
        "válido por 30 minutos.",
    ),
    (
        "cadastro",
        "Como excluo minha conta?",
        "Acesse 'Minha Conta' > 'Privacidade' > 'Solicitar Exclusão'. O processo leva até "
        "30 dias e é irreversível.",
    ),
    # --- Suporte ---
    (
        "suporte",
        "Como entro em contato com o suporte?",
        "Via chat no app (8h–22h), e-mail (resposta em 24h) ou telefone 0800 para urgências.",
    ),
    (
        "suporte",
        "Tive um problema com o vendedor. O que faço?",
        "Acesse o pedido e clique em 'Abrir Disputa'. A mediação analisa em até 3 dias úteis "
        "após ambas as partes enviarem evidências.",
    ),
    (
        "suporte",
        "O vendedor não respondeu minha mensagem. O que fazer?",
        "Vendedores têm até 48 horas para responder. Após isso, clique em 'Solicitar Mediação'.",
    ),
    (
        "suporte",
        "Como avalio uma compra?",
        "Após confirmação de entrega, você recebe notificação para avaliar. Também disponível "
        "em 'Meus Pedidos' > 'Avaliar'.",
    ),
    (
        "suporte",
        "Recebi um produto diferente do anunciado. O que faço?",
        "Acesse o pedido, clique em 'Reportar Problema' > 'Produto diferente do anunciado' "
        "e envie fotos como evidência.",
    ),
    # --- Segurança de conta ---
    (
        "seguranca",
        "Como ativo a autenticação de dois fatores?",
        "Acesse 'Minha Conta' > 'Segurança' > 'Autenticação em Dois Fatores' e siga as "
        "instruções para vincular um aplicativo autenticador.",
    ),
    (
        "seguranca",
        "Suspeito que minha conta foi acessada por outra pessoa. O que faço?",
        "Altere sua senha imediatamente, revogue todas as sessões em 'Segurança' > 'Sessões' "
        "e entre em contato com o suporte.",
    ),
    (
        "seguranca",
        "Recebi um e-mail suspeito em nome do PayChat. O que fazer?",
        "Não clique em nenhum link. Encaminhe para seguranca@paychat.com.br. "
        "O PayChat nunca solicita senha por e-mail.",
    ),
    (
        "seguranca",
        "Como encerro as sessões ativas em outros dispositivos?",
        "Acesse 'Minha Conta' > 'Segurança' > 'Sessões Ativas' e clique em 'Encerrar Todas' "
        "ou selecione dispositivos específicos.",
    ),
    (
        "seguranca",
        "Meus dados são compartilhados com terceiros?",
        "Apenas com parceiros necessários para a operação (transportadoras, gateways de "
        "pagamento), conforme nossa Política de Privacidade e a LGPD.",
    ),
]
