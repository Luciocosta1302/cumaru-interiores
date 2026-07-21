# Cumaru Interiores — Landing Page Conceito

> Landing page para uma marcenaria autoral amazônica fictícia, com modelo 3D interativo, funcionamento offline e design responsivo. Projeto de estudo/portfólio.

**🔗 Demo ao vivo:** [adicionar link após publicar]

![Preview desktop](docs/preview-desktop.png)
![Preview mobile](docs/preview-mobile.png)

---

## Contexto

**Cumaru Interiores** é uma marca fictícia criada para este estudo: uma marcenaria autoral de Belém-PA que trabalha com madeiras amazônicas de manejo certificado (cumaru, ipê, freijó). Todo o conteúdo — nomes, depoimentos, preços e história — é ficcional.

O desafio que me propus: **construir a vitrine digital ideal para um pequeno negócio do Norte do Brasil**, considerando as restrições reais da região — celulares de entrada, conexões instáveis e donos de negócio sem equipe técnica.

## O problema

Pequenos negócios locais raramente têm site, e quando têm, dependem de construtores pesados, cheios de dependências externas que quebram em conexão ruim. Eu queria o oposto:

- Um **arquivo HTML único** que abre em qualquer navegador, até offline;
- Visual de marca autoral, não de template;
- Um elemento "uau" (o 3D) que funcione em celular modesto;
- Hierarquia de informação pensada para quem decide compra pelo WhatsApp.

## Decisões de design

- **Tipografia:** Playfair Display (títulos, serifada clássica) + Inter (texto), inspiradas em referências de sites de woodworking artesanal.
- **Paleta:** creme, chocolate e caramelo — derivada das próprias amostras de madeira usadas no site. Sem cores fora do universo do material.
- **Cards de coleção como amostras de madeira:** em vez de fotos de ambiente genéricas, cada linha de produto exibe a textura da madeira correspondente (cumaru, freijó, ipê, marupá) — o cliente escolhe pela matéria-prima, como numa marcenaria de verdade.
- **Hierarquia mobile própria:** no celular, a ordem é título → modelo 3D → descrição → ações, com tudo centralizado. Conteúdo primeiro, efeito depois.
- **Quebras de linha balanceadas** (`text-wrap: balance` / `pretty`) e ritmo vertical consistente entre seções.
- **Acessibilidade de movimento:** todas as animações (scroll reveal, rotação 3D, partículas) respeitam `prefers-reduced-motion`.

## Decisões técnicas

### Pipeline do modelo 3D

O destaque do projeto. Parti de um modelo `.obj` de mesa com **8,9 MB e ~88 mil vértices** (pernas torneadas exportadas do Blender em altíssima resolução) — inviável para web mobile. Sem bibliotecas de geometria disponíveis, escrevi o pipeline em **Python puro**:

1. **Parse do OBJ** e descarte de geometria de cena (plano de fundo do Blender);
2. **Decimação por vertex clustering** — agrupamento de vértices em grade 3D adaptativa ao bounding box;
3. **Triangulação** com remoção de faces degeneradas;
4. **Geração de UVs por box-mapping** (o modelo veio sem coordenadas de textura): cada face recebe projeção pelo eixo dominante da sua normal;
5. **Empacotamento binário** (posições Float32 + UVs) em base64, embutido no HTML.

**Resultado: 8,9 MB → ~295 KB de geometria** (~9,3 mil vértices), renderizada com Three.js r128, textura de madeira real com repetição, luz quente direcional e correção sRGB.

### Arquitetura "arquivo único"

- Todas as 11 imagens (texturas, fotos de peças, fundo) comprimidas via Pillow e embutidas como data URIs;
- Sem build, sem framework, sem servidor: HTML + CSS + JS vanilla em ~2 MB;
- Fallbacks em camadas: se o CDN do Three.js falhar, a página funciona sem 3D; gradientes de madeira por trás de cada imagem caso algo não carregue.

### Interação

- Rotação automática suave do modelo + arrasto por mouse/toque com easing;
- Partículas de "serragem" em queda lenta ao redor da peça;
- Scroll reveal com `IntersectionObserver`.

## Stack

| Camada | Ferramenta |
|---|---|
| Estrutura | HTML5 + CSS3 (grid areas, custom properties) |
| 3D | Three.js r128 (WebGL) |
| Processamento do modelo | Python 3 (stdlib) |
| Compressão de imagens | Python + Pillow |
| Fontes | Google Fonts (Playfair Display, Inter) |

## Como rodar

```bash
# não precisa de nada além de um navegador:
# baixe cumaru-interiores.html e abra com dois cliques
```

Para regenerar o modelo 3D a partir de um novo `.obj`:

```bash
python3 process_obj.py   # gera o payload compacto
python3 apply_textures.py # embute texturas e atualiza o HTML
```

## Créditos e transparência

- Marca, pessoas, depoimentos e preços são **fictícios**;
- Fotos de peças e texturas de madeira: bancos de imagem e material de referência de terceiros, usados apenas para fins de demonstração;
- Modelo 3D da mesa: arquivo de estudo processado e otimizado por mim.

## Autor

**Lúcio Henrique Ribeiro Costa**
Estudante de Sistemas de Informação (UNIFESSPA) · Desenvolvedor em Marabá-PA
[LinkedIn](adicionar) · [GitHub](adicionar)
