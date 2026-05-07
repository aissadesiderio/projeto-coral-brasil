# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Execução Local (site offline)

- **status:** sem deploy público
- **objetivo:** reestruturação de backend e banco
- **critérios para voltar ao ar:**
  - backend estabilizado (APIs e jobs validados)
  - migrações e consistência do banco concluídas
  - integrações externas reativadas com monitoramento

### Flag de indisponibilidade pública

Para rodar o frontend em modo local/offline, crie um `.env` no diretório `frontend/` com:

```env
REACT_APP_PUBLIC_OFFLINE=true
```

Com a flag ativa, chamadas públicas de produção são neutralizadas na interface.

### Estrutura de páginas (site offline)

- **Página inicial (introdução):** cabeçalho com nome do projeto no canto superior esquerdo + atalhos para *Escolha de Recifes* e *Banco de Dados Geral*.
- **Banco de Dados Geral:** lista de dados de predição e adicionais com download, com filtros de busca por data (início/fim ou publicação), localização (estado/cidade) e fonte (Copernicus, NOAA, NCBI, NASA).
- **Localizações de Corais:** cards com foto, nome do local e número de informações disponíveis; ao clicar, abre a página específica do local.
- **Mídia no modo offline:** as imagens de locais usam apenas assets locais do frontend (sem dependência de links externos).
- **Página do local específico:** apresenta informações do local e o painel de risco apenas quando houver variáveis suficientes para predição.

### Backend local (Django/settings)

A configuração local do backend agora usa:

- `DJANGO_DEBUG` para controlar `DEBUG`
- `ALLOWED_HOSTS` restrito a `localhost` e `127.0.0.1`
- integrações de deploy/cloud desativadas (`USE_S3_STORAGE`, `ENABLE_AWS_SERVICES`, `ENABLE_EXTERNAL_TASKS`)

Exemplo de variáveis:

```env
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=chave-local
```

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
