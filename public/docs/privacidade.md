# Política de Privacidade — [NEV]²

**Última atualização:** 01/09/2026

Esta Política de Privacidade descreve como o [NEV]² Restaurant Management System (doravante "[NEV]²" ou "Sistema") trata os dados pessoais no contexto de seu uso, em conformidade com a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 — LGPD).

## 1. Quem trata os dados

O [NEV]² é o controlador dos dados pessoais tratados através do sistema, sendo responsável por [[NEV]²Thi_ii] e [[NEV]²Henriique__].

## 2. Quais dados coletamos

### 2.1. Usuários do sistema (equipe do Restaurante Cliente)

Consideram-se "usuários" apenas as pessoas cadastradas pelo próprio Restaurante Cliente para operar o sistema, nos perfis Dono e Garçom. Para esses usuários, coletamos e armazenamos:

- ID de identificação no sistema;
- E-mail;
- Nome completo;
- Cargo (perfil de acesso);
- ID do restaurante ao qual está vinculado;
- Status da conta (ativo/inativo).

A senha do usuário **nunca é armazenada em texto legível**: ela é convertida em um hash criptográfico (BCrypt) no momento do cadastro, e esse processo é irreversível — nem mesmo o [NEV]² tem acesso à senha original do usuário. A senha também nunca é retornada em nenhuma resposta do sistema (o schema de leitura de usuário — UserRead — não inclui esse campo).

### 2.2. Consumidores finais (clientes do restaurante, que fazem pedidos pela mesa)

O sistema **não coleta dados pessoais dos consumidores finais**. O consumidor não cria conta, não faz login e não possui senha no sistema. Quando um pedido é realizado, o sistema associa esse pedido apenas à Mesa correspondente — não é solicitado nome, e-mail, telefone, CPF ou qualquer outro dado de identificação do consumidor.

Ou seja: não há, nesta versão do sistema, dados pessoais de consumidores finais sendo tratados.

## 3. Para que usamos os dados coletados

Os dados dos usuários (Dono e Garçom) são utilizados exclusivamente para:

- Permitir o acesso autenticado ao sistema;
- Controlar permissões de acordo com o cargo de cada usuário;
- Identificar qual restaurante cada usuário representa;
- Viabilizar comunicação relacionada ao funcionamento do serviço (ex: suporte, avisos sobre a conta).

## 4. Com quem compartilhamos os dados

O [NEV]² não vende, aluga ou compartilha os dados dos usuários com terceiros para fins comerciais ou publicitários.

Os dados podem ser acessados por:

- Provedores de hospedagem/infraestrutura utilizados para operar o sistema (atualmente Render, Neon.tech, Upstash e Vercel), estritamente para fins de armazenamento e funcionamento técnico;
- Autoridades competentes, mediante obrigação legal ou ordem judicial.

## 5. Onde os dados ficam armazenados

Os dados são armazenados e processados através da seguinte infraestrutura:

- **Banco de dados (PostgreSQL)**: hospedado na Neon.tech;
- **API/Backend**: hospedado na Render;
- **Sessões**: gerenciadas via Redis, hospedado na Upstash;
- **Interface/Site**: hospedada na Vercel (não armazena dados pessoais, apenas serve a interface).

Todos esses provedores atuam como operadores de dados em nome do [NEV]², utilizados estritamente para viabilizar o funcionamento técnico do sistema.

## 6. Por quanto tempo guardamos os dados

Os dados de usuários são mantidos enquanto a conta do Restaurante Cliente estiver ativa. Em caso de cancelamento do serviço, os dados poderão ser mantidos por um período adicional razoável para fins de backup, obrigação legal ou resolução de eventuais pendências, sendo excluídos posteriormente.

## 7. Direitos do titular dos dados

Nos termos da LGPD, qualquer usuário cujos dados sejam tratados pelo [NEV]² pode solicitar:

- Confirmação da existência de tratamento de seus dados;
- Acesso aos dados armazenados;
- Correção de dados incompletos, inexatos ou desatualizados;
- Exclusão dos dados, observadas as exceções legais;
- Informação sobre com quem os dados foram compartilhados;
- Revogação de consentimento, quando aplicável.

Solicitações podem ser feitas diretamente ao Restaurante Cliente responsável pelo cadastro do usuário, ou diretamente ao [NEV]² através dos canais de contato informados na proposta comercial.

## 8. Segurança dos dados

O [NEV]² adota medidas técnicas para proteger os dados armazenados, incluindo:

- Criptografia de senha via hash (BCrypt), impedindo o acesso à senha original mesmo em caso de acesso não autorizado ao banco de dados;
- Controle de acesso por perfil (Dono e Garçom), restringindo o que cada usuário pode visualizar ou modificar.

Nenhum sistema é 100% livre de riscos. Em caso de incidente de segurança que envolva dados pessoais, o [NEV]² se compromete a notificar os Restaurantes Clientes afetados em prazo razoável, conforme exigido pela LGPD.

## 9. Alterações nesta Política

Esta Política pode ser atualizada periodicamente, especialmente à medida que o sistema evoluir e passar a coletar novos tipos de dados (por exemplo, caso futuramente sejam adicionados dados de consumidores finais). Alterações relevantes serão comunicadas aos Restaurantes Clientes com antecedência razoável.

## 10. Contato

Dúvidas sobre esta Política podem ser encaminhadas a [[NEV]²Thi_ii] ou [[NEV]²Henriique__], responsáveis pelo [NEV]².

---

**[NEV]²**
Desenvolvido por [[NEV]²Thi_ii] e [[NEV]²Henriique__]
