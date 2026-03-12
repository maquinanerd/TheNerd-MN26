import logging
import requests
import time
import json
import re 
import html as _html
from .html_utils import detect_forbidden_cta, strip_forbidden_cta_sentences
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def _slugify(name: str) -> str:
    """Creates a simple, WordPress-compatible slug from a string."""
    s = name.strip().lower()
    # Remove characters that are not alphanumeric, whitespace, or hyphen
    s = re.sub(r'[^\w\s-]', '', s, flags=re.UNICODE)
    # Replace whitespace and underscores with a hyphen
    s = re.sub(r'[\s_-]+', '-', s, flags=re.UNICODE)
    # Strip leading/trailing hyphens and limit length
    return s.strip('-')[:190] or 'tag'

class WordPressClient:
    """A client for interacting with the WordPress REST API."""

    def __init__(self, config: Dict[str, str], categories_map: Dict[str, int]):
        self.api_url = (config.get('url') or "").rstrip('/')
        if not self.api_url:
            raise ValueError("WORDPRESS_URL is not configured.")
        self.user = config.get('user')
        self.password = config.get('password')
        self.categories_map = categories_map
        self.session = requests.Session()
        if self.user and self.password:
            self.session.auth = (self.user, self.password)
        self.session.headers.update({'User-Agent': 'VocMoney-Pipeline/1.0'})

    def get_domain(self) -> str:
        """Extracts the domain from the WordPress URL."""
        try:
            return urlparse(self.api_url).netloc
        except Exception:
            return ""

    def _get_existing_tag_id(self, name: str) -> Optional[int]:
        """Searches for an existing tag by name or slug and returns its ID."""
        slug = _slugify(name)
        tags_endpoint = f"{self.api_url}/tags"
        params = {"search": name, "per_page": 100}

        try:
            r = self.session.get(tags_endpoint, params=params, timeout=20)
            r.raise_for_status()
            items = r.json()
            
            # WordPress search can be broad, so we verify the match
            for item in items:
                if item.get('name', '').strip().lower() == name.strip().lower():
                    return int(item['id'])
            for item in items:
                if item.get('slug') == slug:
                    return int(item['id'])
        except requests.RequestException as e:
            logger.error(
                f"❌ ERRO ao buscar tag '{name}' | "
                f"Exceção: {type(e).__name__} | "
                f"Mensagem: {str(e)[:200]}"
            )
        
        return None

    def _create_tag(self, name: str) -> Optional[int]:
        """Creates a new tag and returns its ID."""
        tags_endpoint = f"{self.api_url}/tags"
        payload = {"name": name, "slug": _slugify(name)}
        
        try:
            r = self.session.post(tags_endpoint, json=payload, timeout=20)
            
            if r.status_code in (200, 201):
                tag_id = int(r.json()['id'])
                logger.info(f"✅ Tag criada com sucesso | Nome: '{name}' | ID: {tag_id} | Tempo: {r.elapsed.total_seconds():.2f}s")
                return tag_id
            
            # Handle race condition where tag was created between search and post
            if r.status_code == 400 and isinstance(r.json(), dict) and r.json().get("code") == "term_exists":
                logger.warning(f"⚠️  Tag '{name}' já existe (race condition). Re-buscando ID...")
                return self._get_existing_tag_id(name)
            
            logger.error(
                f"❌ ERRO ao criar tag '{name}' | "
                f"Status: {r.status_code} | "
                f"Endpoint: {tags_endpoint} | "
                f"Resposta: {r.text[:300]}"
            )
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error(
                f"❌ ERRO na requisição ao criar tag '{name}' | "
                f"Exceção: {type(e).__name__} | "
                f"Mensagem: {str(e)[:200]}"
            )
            if e.response is not None:
                logger.error(f"   Response Status: {e.response.status_code}")
                logger.error(f"   Response Body: {e.response.text[:300]}")

        return None

    def _ensure_tag_ids(self, tags: List[Any], max_tags: int = 10) -> List[int]:
        """Converts a list of tag names/IDs into a list of integer IDs, creating tags if necessary."""
        if not tags:
            return []

        # Normalize input (handles strings, ints, and comma-separated strings)
        norm_tags: List[str] = []
        for t in tags:
            if isinstance(t, int):
                norm_tags.append(str(t))
            elif isinstance(t, str):
                norm_tags.extend([p.strip() for p in t.split(',') if p.strip()])
        
        # Deduplicate and limit
        cleaned_tags = list(dict.fromkeys(norm_tags))[:max_tags]
        
        tag_ids: List[int] = []
        for tag_name in cleaned_tags:
            if tag_name.isdigit():
                tag_ids.append(int(tag_name))
            elif len(tag_name) >= 2:
                tag_id = self._get_existing_tag_id(tag_name) or self._create_tag(tag_name)
                if tag_id:
                    tag_ids.append(tag_id)
        
        logger.info(f"Resolved tags {tags} to IDs: {tag_ids}")
        return tag_ids

    def _get_existing_category_id(self, name: str) -> Optional[int]:
        """Searches for an existing category by name or slug and returns its ID."""
        slug = _slugify(name)
        endpoint = f"{self.api_url}/categories"
        # WordPress category search is not as reliable as tag search, so we get more results and filter
        params = {"search": name, "per_page": 100}

        try:
            r = self.session.get(endpoint, params=params, timeout=20)
            r.raise_for_status()
            items = r.json()
            
            # Exact match on name (case-insensitive)
            for item in items:
                if item.get('name', '').strip().lower() == name.strip().lower():
                    return int(item['id'])
            # Match on slug
            for item in items:
                if item.get('slug') == slug:
                    return int(item['id'])
        except requests.RequestException as e:
            logger.error(
                f"❌ ERRO ao buscar categoria '{name}' | "
                f"Exceção: {type(e).__name__} | "
                f"Mensagem: {str(e)[:200]}"
            )
        
        return None

    def _create_category(self, name: str) -> Optional[int]:
        """Creates a new category and returns its ID."""
        endpoint = f"{self.api_url}/categories"
        payload = {"name": name, "slug": _slugify(name)}
        
        try:
            r = self.session.post(endpoint, json=payload, timeout=20)
            
            if r.status_code in (200, 201):
                cat_id = int(r.json()['id'])
                logger.info(f"✅ Categoria criada com sucesso | Nome: '{name}' | ID: {cat_id} | Tempo: {r.elapsed.total_seconds():.2f}s")
                return cat_id
            
            if r.status_code == 400 and isinstance(r.json(), dict) and r.json().get("code") == "term_exists":
                logger.warning(f"⚠️  Categoria '{name}' já existe (race condition). Re-buscando ID...")
                return self._get_existing_category_id(name)
            
            logger.error(
                f"❌ ERRO ao criar categoria '{name}' | "
                f"Status: {r.status_code} | "
                f"Endpoint: {endpoint} | "
                f"Resposta: {r.text[:300]}"
            )
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error(
                f"❌ ERRO na requisição ao criar categoria '{name}' | "
                f"Exceção: {type(e).__name__} | "
                f"Mensagem: {str(e)[:200]}"
            )
            if e.response is not None:
                logger.error(f"   Response Status: {e.response.status_code}")
                logger.error(f"   Response Body: {e.response.text[:300]}")

        return None

    def resolve_category_names_to_ids(self, category_names: List[str]) -> List[int]:
        """Converts a list of category names into a list of integer IDs, creating categories if necessary."""
        if not category_names:
            return []

        # Deduplicate while preserving order (for logging)
        cleaned_names = list(dict.fromkeys([name.strip() for name in category_names if name.strip() and len(name) >= 1]))
        
        cat_ids: List[int] = []
        for name in cleaned_names:
            # Check local map first (from config)
            cat_id = self.categories_map.get(name)
            if not cat_id:
                # Case-insensitive check on local map
                for map_name, map_id in self.categories_map.items():
                    if map_name.lower() == name.lower():
                        cat_id = map_id
                        break
            
            # If not in local map, query WordPress
            if not cat_id:
                cat_id = self._get_existing_category_id(name) or self._create_category(name)

            if cat_id:
                cat_ids.append(cat_id)
        
        logger.info(f"Resolved category names {cleaned_names} to IDs: {cat_ids}")
        return cat_ids

    def upload_media_from_url(self, image_url: str, alt_text: str = "", max_attempts: int = 3) -> Optional[Dict[str, Any]]:
        """
        Downloads an image and uploads it to WordPress with a retry mechanism.
        """
        last_err = None
        for attempt in range(1, max_attempts + 1):
            try:
                # 1. Download the image with a reasonable timeout
                img_response = requests.get(image_url, timeout=25)
                img_response.raise_for_status()
                content_type = img_response.headers.get('Content-Type', 'image/jpeg')
                img_size = len(img_response.content)
                # Sanitize filename
                filename = (urlparse(image_url).path.split('/')[-1] or "image.jpg").split("?")[0]

                # 2. Upload to WordPress
                media_endpoint = f"{self.api_url}/media"
                headers = {
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': content_type,
                }
                wp_response = self.session.post(media_endpoint, headers=headers, data=img_response.content, timeout=40)
                wp_response.raise_for_status()
                media_id = wp_response.json().get('id')
                logger.info(f"MEDIA OK: ID {media_id} | {filename} ({img_size} bytes)")
                logger.debug(f"  Content-Type: {content_type}")
                logger.debug(f"  Tempo: {wp_response.elapsed.total_seconds():.2f}s")
                return wp_response.json() # Success

            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = e
                logger.warning(f"MEDIA RETRY {attempt}/{max_attempts}: {type(e).__name__} | Aguardando {2*attempt}s...")
                time.sleep(2 * attempt)  # Simple backoff
            except Exception as e:
                last_err = e
                logger.error(f"MEDIA ERRO ({attempt}/{max_attempts}): {type(e).__name__}: {str(e)[:150]}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"  Status: {e.response.status_code}")
                    try:
                        resp_json = e.response.json()
                        logger.error(f"  Erro WordPress: {resp_json.get('code', 'N/A')} - {resp_json.get('message', 'N/A')[:200]}")
                    except:
                        logger.error(f"  Response: {e.response.text[:300]}")
                break # Don't retry on WP errors (4xx, 5xx) or other issues

        logger.error(f"MEDIA FALHOU: {filename} apos {attempt} tentativa(s) | Erro: {type(last_err).__name__}")
        return None

    def set_media_alt_text(self, media_id: int, alt_text: str) -> bool:
        """Sets the alt text for a media item in WordPress."""
        if not alt_text:
            return False
        try:
            endpoint = f"{self.api_url}/media/{media_id}"
            payload = {"alt_text": alt_text}
            r = self.session.post(endpoint, json=payload, timeout=20)
            r.raise_for_status()
            logger.info(f"Successfully set alt text for media ID {media_id}.")
            return True
        except requests.RequestException as e:
            logger.warning(f"Failed to set alt_text on media {media_id}: {e}")
            if e.response is not None:
                logger.warning(f"Response body: {e.response.text}")
            return False

    def find_related_posts(self, term: str, limit: int = 3) -> List[Dict[str, str]]:
        """Searches for posts on the site and returns their title and URL."""
        if not term:
            return []
        try:
            endpoint = f"{self.api_url}/search"
            params = {"search": term, "per_page": limit, "_embed": "self"}
            resp = self.session.get(endpoint, params=params, timeout=15)
            resp.raise_for_status()
            # The 'url' in the search result is the API URL, we need the 'link' from the embedded post object
            return [{"title": i.get("title", ""), "url": i.get("_embedded", {}).get("self", [{}])[0].get("link", "")} for i in resp.json()]
        except requests.RequestException as e:
            logger.error(f"Error searching for related posts with term '{term}': {e}")
            return []

    def create_post(self, payload: Dict[str, Any]) -> Optional[int]:
        """Creates a new post in WordPress."""
        try:
            # Validar tamanho do payload ANTES de enviar
            payload_size = len(json.dumps(payload))
            post_title = payload.get('title', 'SEM TITULO')[:60]
            
            # Se exceder 30KB, tentar reduzir conteúdo
            if payload_size > 30000:  # 30KB limit (mais realista que 15KB)
                logger.warning(f"POST GRANDE: {payload_size} bytes (limite: 30KB). Tentando reduzir conteúdo...")
                
                # Estratégia 1: Remover parágrafos repetitivos ou muito curtos
                if 'content' in payload and payload['content']:
                    content = payload['content']
                    # Remove múltiplos parágrafos vazios
                    content = re.sub(r'<!-- /wp:paragraph -->\s*<!-- wp:paragraph -->', '', content)
                    # Remove parágrafos com menos de 30 chars
                    content = re.sub(r'<!-- wp:paragraph -->\s*<p>\s*.{0,25}\s*<\/p>\s*<!-- /wp:paragraph -->', '', content, flags=re.IGNORECASE)
                    payload['content'] = content
                    
                    # Recalcular tamanho após redução
                    new_payload_size = len(json.dumps(payload))
                    logger.info(f"Conteúdo reduzido: {payload_size} → {new_payload_size} bytes")
                    payload_size = new_payload_size
            
            if payload_size > 30000:  # Ainda muito grande
                logger.error(f"POST GRANDE DEMAIS: {payload_size} bytes (limite: 30KB)")
                logger.error(f"  Titulo: {post_title}")
                logger.error(f"  Content: {len(payload.get('content', ''))} chars")
                logger.error(f"  Featured media: {payload.get('featured_media')}")
                return None
            
            # Resolve tag names to integer IDs before sending
            if 'tags' in payload and payload['tags']:
                payload['tags'] = self._ensure_tag_ids(payload['tags'])

            posts_endpoint = f"{self.api_url}/posts"
            payload.setdefault('status', 'publish')
            
            # Clean up payload: remove fields WordPress REST API doesn't accept
            # Only send recognized fields to avoid 500 errors
            safe_fields = ['title', 'slug', 'content', 'excerpt', 'categories', 'tags', 'featured_media', 'status']
            clean_payload = {k: v for k, v in payload.items() if k in safe_fields}
            
            # Remove featured_media if it's 0 or None (invalid)
            if 'featured_media' in clean_payload:
                if not clean_payload['featured_media'] or clean_payload['featured_media'] == 0:
                    logger.warning("Featured media ID is invalid (0 or None). Removing from payload.")
                    del clean_payload['featured_media']
                else:
                    # Ensure it's an integer
                    clean_payload['featured_media'] = int(clean_payload['featured_media'])
            
            # Ensure title is plain text (no HTML tags)
            if 'title' in clean_payload and clean_payload['title']:
                title = clean_payload['title']
                # Remove any HTML tags that might have leaked into the title
                title = re.sub(r'<[^>]+>', '', title).strip()
                clean_payload['title'] = title
            
            # Sanitize content to prevent malformed HTML
            if 'content' in clean_payload and clean_payload['content']:
                content = clean_payload['content']
                # Replace problematic whitespace characters
                content = content.replace('\u00a0', ' ')  # Non-breaking space
                content = content.replace('\u2002', ' ')  # En space
                content = content.replace('\u2003', ' ')  # Em space
                content = content.replace('\u200b', '')   # Zero-width space (remove)
                # Remove only truly problematic control characters (not whitespace)
                content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t' or ord(char) in [0x0B])
                # Clean up multiple consecutive spaces (but keep single spaces)
                content = re.sub(r' {2,}', ' ', content)
                clean_payload['content'] = content
            
            # Sanitize excerpt
            if 'excerpt' in clean_payload and clean_payload['excerpt']:
                excerpt = clean_payload['excerpt']
                excerpt = excerpt.replace('\u00a0', ' ')
                excerpt = ''.join(char for char in excerpt if ord(char) >= 32 or char in '\n\r\t')
                clean_payload['excerpt'] = excerpt
            
            # Sanitize title
            if 'title' in clean_payload and clean_payload['title']:
                title = clean_payload['title']
                title = title.replace('\u00a0', ' ')
                title = ''.join(char for char in title if ord(char) >= 32 or char in '\n\r\t')
                clean_payload['title'] = title
            
            # Ensure minimum content length
            if 'content' not in clean_payload or not clean_payload.get('content', '').strip():
                logger.error("POST ERRO: Conteudo vazio. Cancelando publicacao")
                return None
            
            content_length = len(clean_payload['content'])
            if content_length < 100:
                logger.error(f"POST ERRO: Conteudo muito curto ({content_length} chars). Minimo: 100 chars")
                return None
            
            # Validar título
            if 'title' not in clean_payload or not clean_payload.get('title', '').strip():
                logger.error("POST ERRO: Titulo vazio. Cancelando publicacao")
                return None
            
            title_length = len(clean_payload['title'])
            if title_length < 3:
                logger.error(f"POST ERRO: Titulo muito curto ({title_length} chars). Minimo: 3 chars")
                return None
            
            # Ensure categories is a valid list of integers
            if 'categories' in clean_payload and clean_payload['categories']:
                try:
                    clean_payload['categories'] = [int(c) for c in clean_payload['categories'] if c]
                except (ValueError, TypeError) as e:
                    logger.warning(f"Categorias invalidas, removendo: {e}")
                    del clean_payload['categories']
            
            # VALIDAR CATEGORIAS - remover as que não existem no WordPress
            if 'categories' in clean_payload and clean_payload['categories']:
                try:
                    valid_categories = []
                    cats_endpoint = f"{self.api_url}/categories"
                    
                    # Buscar todas as categorias disponíveis
                    all_cats_response = self.session.get(
                        cats_endpoint, 
                        params={"per_page": 100, "orderby": "id", "order": "asc"},
                        timeout=30
                    )
                    
                    if all_cats_response.ok:
                        all_cats = all_cats_response.json()
                        valid_cat_ids = set(cat['id'] for cat in all_cats)
                        
                        # Filtrar apenas categorias que existem
                        for cat_id in clean_payload['categories']:
                            if cat_id in valid_cat_ids:
                                valid_categories.append(cat_id)
                            else:
                                logger.warning(f"⚠️  Categoria {cat_id} não existe no WordPress, removendo")
                        
                        if valid_categories:
                            clean_payload['categories'] = valid_categories
                            logger.info(f"✅ Categorias validadas: {valid_categories}")
                        else:
                            logger.warning("⚠️  Nenhuma categoria válida encontrada, removendo todas")
                            del clean_payload['categories']
                    else:
                        logger.warning(f"Não conseguiu validar categorias (erro {all_cats_response.status_code}), enviando assim mesmo")
                        
                except Exception as cat_err:
                    logger.warning(f"Erro ao validar categorias: {cat_err}, enviando assim mesmo")
            
            # Log ANTES da requisição - informação resumida
            post_title = clean_payload.get('title', 'SEM TITULO')[:80]
            logger.info(f"POST CRIAR: '{post_title}'")
            logger.info(f"  WP payload: title_len={len(clean_payload.get('title', ''))} content_len={len(clean_payload.get('content', ''))} cat={clean_payload.get('categories', [])} tags={clean_payload.get('tags', [])}")
            
            # Validação extra: tentar serializar para JSON e validar
            try:
                test_json = json.dumps(clean_payload, ensure_ascii=False)
                logger.debug(f"JSON válido: {len(test_json)} bytes")
            except Exception as json_err:
                logger.error(f"ERRO: Payload não é JSON válido: {str(json_err)[:200]}")
                logger.error(f"  Título: {clean_payload.get('title')[:100]}")
                logger.error(f"  Conteúdo (primeiros 100): {clean_payload.get('content', '')[:100]}")
                return None
            logger.debug(f"  - Tamanho conteudo: {len(clean_payload.get('content', ''))} chars")
            logger.debug(f"  - Featured image: {clean_payload.get('featured_media', 'nenhuma')}")
            logger.debug(f"  - Categorias: {clean_payload.get('categories', [])}")
            logger.debug(f"  - Tags: {clean_payload.get('tags', [])}")
            
            # Log do payload completo APENAS em DEBUG mode
            if logger.isEnabledFor(logging.DEBUG):
                try:
                    log_payload = json.dumps(clean_payload, indent=2, ensure_ascii=False)[:2000]
                    logger.debug(f"PAYLOAD JSON:\n{log_payload}")
                except Exception as log_e:
                    logger.warning(f"Nao conseguiu serializar payload: {log_e}")

            response = self.session.post(posts_endpoint, json=clean_payload, timeout=60)
            
            # Log DEPOIS da resposta
            post_id = response.json().get('id') if response.ok else None
            
            if response.ok and post_id and post_id > 0:  # Validar que tem ID válido
                logger.info(f"POST OK: ID {post_id} criado com sucesso em {response.elapsed.total_seconds():.2f}s")
                return post_id
            elif response.status_code == 500:
                # ERRO 500 - CAPTURAR TUDO PARA DEBUG DETALHADO
                logger.error("=" * 100)
                logger.error("🔴 ERRO 500 DO WORDPRESS - ANÁLISE COMPLETA")
                logger.error("=" * 100)
                
                # 1. Informações da requisição
                logger.error(f"REQUISIÇÃO ENVIADA:")
                logger.error(f"  URL: {posts_endpoint}")
                logger.error(f"  Método: POST")
                logger.error(f"  Auth: {'Sim (Basic Auth)' if self.user else 'Não'}")
                logger.error(f"  Headers: {dict(self.session.headers)}")
                logger.error(f"  Tamanho do payload: {len(json.dumps(clean_payload))} bytes")
                
                # 2. Conteúdo enviado (payload completo)
                logger.error(f"\nPAYLOAD ENVIADO (JSON COMPLETO):")
                try:
                    payload_json = json.dumps(clean_payload, indent=2, ensure_ascii=False)
                    logger.error(payload_json)
                except Exception as e:
                    logger.error(f"Erro ao serializar payload: {e}")
                
                # 3. Resposta do WordPress (TUDO)
                logger.error(f"\nRESPOSTA DO WORDPRESS:")
                logger.error(f"  Status Code: {response.status_code}")
                logger.error(f"  Headers Response: {dict(response.headers)}")
                logger.error(f"  Content-Type: {response.headers.get('content-type')}")
                logger.error(f"  Content-Length: {len(response.text)} bytes")
                
                # 4. Corpo da resposta (COMPLETO, não truncado)
                logger.error(f"\nCORPO DA RESPOSTA (COMPLETO):")
                logger.error(f"{response.text}")
                
                # 5. Tentar parsear como JSON
                logger.error(f"\nANÁLISE JSON DA RESPOSTA:")
                try:
                    resp_json = response.json()
                    logger.error(json.dumps(resp_json, indent=2, ensure_ascii=False))
                except Exception as json_err:
                    logger.error(f"  Não é JSON válido: {json_err}")
                    logger.error(f"  Tipo MIME: {response.headers.get('content-type')}")
                
                # 6. Salvar em arquivo de debug
                debug_file = f"debug/wordpress_error_500_{int(time.time())}.txt"
                try:
                    import os
                    os.makedirs('debug', exist_ok=True)
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"ERRO 500 - {post_title}\n")
                        f.write("=" * 100 + "\n\n")
                        f.write(f"PAYLOAD ENVIADO:\n{json.dumps(clean_payload, indent=2, ensure_ascii=False)}\n\n")
                        f.write(f"RESPOSTA WORDPRESS:\n{response.text}\n")
                    logger.error(f"  ✅ Debug salvo em: {debug_file}")
                except Exception as file_err:
                    logger.error(f"  ❌ Erro ao salvar debug: {file_err}")
                
                logger.error("=" * 100)
                logger.error("❌ TENTANDO NOVAMENTE...")
                logger.error("=" * 100)
                
                # Tentar novamente
                logger.info(f"  Tentativa 2: Reenviando artigo completo (sem remoção de conteúdo)")
                
                try:
                    response2 = self.session.post(posts_endpoint, json=clean_payload, timeout=60)
                    post_id2 = response2.json().get('id') if response2.ok else None
                    
                    if response2.ok and post_id2 and post_id2 > 0:
                        logger.info(f"✅ POST CRIADO NA TENTATIVA 2: ID {post_id2}")
                        return post_id2
                    else:
                        logger.error(f"❌ Tentativa 2 também falhou com status {response2.status_code}")
                        logger.error(f"  Resposta: {response2.text}")
                except Exception as retry_err:
                    logger.error(f"❌ Tentativa 2 exception: {str(retry_err)[:500]}")
            
            # ERRO na criacao - log detalhado
            logger.error(f"WordPress post creation failed with status {response.status_code}: {response.text[:500]}")
            
            # Log a resposta de erro detalhada
            try:
                error_data = response.json()
                error_msg = error_data.get('message', 'sem mensagem')
                error_code = error_data.get('code', 'sem codigo')
                logger.error(f"ERROR - wordpress - WordPress post creation failed with status {response.status_code}")
                logger.error(f"ERROR - wordpress - Failed to create WordPress post: {response.status_code} Server Error: Internal Server Error for url: {posts_endpoint}")
            except:
                pass
                logger.error(f"  Resposta: {response.text[:300]}")
            
            response.raise_for_status()

        except requests.RequestException as e:
            logger.error(f"POST ERRO: Excecao {type(e).__name__}: {str(e)[:200]}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"  Status: {e.response.status_code}")
                try:
                    logger.error(f"  Response JSON: {json.dumps(e.response.json(), indent=2)[:500]}")
                except:
                    logger.error(f"  Response: {e.response.text[:300]}")
            return None

    def get_post_content(self, post_id: int) -> Optional[str]:
        """Fetches the raw content of a post for sanitization checks."""
        endpoint = f"{self.api_url}/posts/{post_id}"
        params = {"context": "edit", "_fields": "content"}
        try:
            r = self.session.get(endpoint, params=params, timeout=30)
            r.raise_for_status()
            data = r.json() or {}
            content = data.get("content", {})
            result = content.get("raw") or content.get("rendered")
            logger.debug(f"✅ Conteúdo do post {post_id} recuperado | Tamanho: {len(result) if result else 0} chars | Tempo: {r.elapsed.total_seconds():.2f}s")
            return result
        except requests.RequestException as e:
            logger.error(
                f"❌ ERRO ao buscar conteúdo do post {post_id} | "
                f"Exceção: {type(e).__name__} | "
                f"Mensagem: {str(e)[:200]} | "
                f"Endpoint: {endpoint}"
            )
            if getattr(e, "response", None) is not None:
                logger.error(f"   Response Status: {e.response.status_code}")
                logger.error(f"   Response Body: {e.response.text[:500]}")
            return None

    def update_post_content(self, post_id: int, content: str) -> bool:
        """Updates the content of an existing post."""
        endpoint = f"{self.api_url}/posts/{post_id}"
        payload = {"content": content}
        try:
            r = self.session.post(endpoint, json=payload, timeout=40)
            if not r.ok:
                logger.error(
                    f"❌ ERRO ao atualizar conteúdo do post {post_id} | "
                    f"Status: {r.status_code} | "
                    f"Tamanho do conteúdo: {len(content)} chars | "
                    f"Tempo: {r.elapsed.total_seconds():.2f}s | "
                    f"Resposta: {r.text[:500]}"
                )
                r.raise_for_status()
            logger.info(f"✅ Conteúdo do post {post_id} atualizado com sucesso | Tamanho: {len(content)} chars | Tempo: {r.elapsed.total_seconds():.2f}s")
            return True
        except requests.RequestException as e:
            logger.error(
                f"❌ ERRO ao atualizar post {post_id} | "
                f"Exceção: {type(e).__name__} | "
                f"Mensagem: {str(e)[:200]} | "
                f"Endpoint: {endpoint}"
            )
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"   Response Status: {e.response.status_code}")
                logger.error(f"   Response Body: {e.response.text[:500]}")
            if getattr(e, "response", None) is not None:
                logger.error(f"Response body: {e.response.text}")
            return False

    def update_post_yoast_seo(self, post_id: int, featured_media_id: int, seo_data: Dict[str, Any]) -> bool:
        """
        Updates Yoast SEO metadata for a post including OG images, meta descriptions, etc.
        This fixes the og:image pointing to external URLs by forcing it to use featured_media.
        
        Args:
            post_id: WordPress post ID
            featured_media_id: ID of the featured image (media ID)
            seo_data: Dictionary containing SEO fields:
                - title: SEO title (60-70 chars)
                - description: Meta description (120-160 chars)  
                - focuskw: Focus keyword
                - title_pt: Portuguese SEO title
                - description_pt: Portuguese meta description
                
        Returns:
            True if update was successful, False otherwise
        """
        try:
            endpoint = f"{self.api_url}/posts/{post_id}"
            
            # Prepare Yoast SEO fields
            # Note: WordPress REST API uses underscore prefix for meta fields in Yoast
            yoast_fields = {
                '_yoast_wpseo_title': seo_data.get('title', '')[:70] or seo_data.get('title_pt', '')[:70],
                '_yoast_wpseo_metadesc': seo_data.get('description', '')[:160] or seo_data.get('description_pt', '')[:160],
                '_yoast_wpseo_focuskw': seo_data.get('focuskw', '')[:30],
                '_yoast_wpseo_opengraph-image': '',  # Will be set below
                '_yoast_wpseo_opengraph-image-id': str(featured_media_id),
                '_yoast_wpseo_content_score': '90',  # Assumed good content
                '_yoast_wpseo_primary_category': '',  # Can be set if needed
            }
            
            # Get featured image URL from WordPress
            if featured_media_id:
                try:
                    media_endpoint = f"{self.api_url}/media/{featured_media_id}"
                    media_resp = self.session.get(media_endpoint, timeout=20)
                    if media_resp.ok:
                        media_data = media_resp.json()
                        image_url = media_data.get('source_url', '')
                        if image_url:
                            yoast_fields['_yoast_wpseo_opengraph-image'] = image_url
                            logger.debug(f"OG Image URL set: {image_url}")
                except Exception as e:
                    logger.warning(f"Could not fetch media URL for ID {featured_media_id}: {e}")
            
            # Build the update payload
            # Yoast fields are sent as meta in WordPress REST API v2
            update_payload = {
                'meta': yoast_fields
            }
            
            # Make the update request
            response = self.session.post(endpoint, json=update_payload, timeout=40)
            
            if response.ok:
                logger.info(f"✅ Yoast SEO metadata atualizado | Post ID: {post_id} | Tempo: {response.elapsed.total_seconds():.2f}s")
                logger.debug(f"   Yoast fields updated: {list(yoast_fields.keys())}")
                return True
            else:
                logger.error(
                    f"❌ ERRO ao atualizar Yoast SEO para post {post_id} | "
                    f"Status: {response.status_code} | "
                    f"Resposta: {response.text[:500]}"
                )
                return False
                
        except requests.RequestException as e:
            logger.error(
                f"❌ ERRO ao atualizar Yoast SEO do post {post_id} | "
                f"Exceção: {type(e).__name__} | "
                f"Mensagem: {str(e)[:200]}"
            )
            return False

    def add_google_news_meta(self, post_id: int, news_data: Dict[str, Any]) -> bool:
        """
        Adds Google News optimized meta tags to a post.
        Improves search rankings for Google News and news aggregators.
        
        Args:
            post_id: WordPress post ID
            news_data: Dictionary with news metadata:
                - keywords: List of keywords (comma-separated, max 10 words)
                - genres: News genres (Blog, Opinion, Review, etc.)
                - standout: Whether this is a standout article (True/False)
                - access: 'Subscription', 'Registration', or 'Free'
                
        Returns:
            True if update was successful, False otherwise
        """
        try:
            endpoint = f"{self.api_url}/posts/{post_id}"
            
            # Prepare Google News meta fields
            keywords = news_data.get('keywords', '')
            if isinstance(keywords, list):
                keywords = ', '.join(keywords)
            keywords = keywords[:256]  # Max length for Google News keywords
            
            genres = news_data.get('genres', 'Blog')
            standout = news_data.get('standout', False)
            access = news_data.get('access', 'Free')
            
            # Google News meta tags (as custom meta)
            news_fields = {
                'googleNews_keywords': keywords,
                'googleNews_genres': genres,
                'googleNews_standout': 'yes' if standout else 'no',
                'googleNews_access': access,
                'article_news_keywords': keywords,  # Alternativa para alguns temas
            }
            
            # Build update payload
            update_payload = {
                'meta': news_fields
            }
            
            # Make the update request
            response = self.session.post(endpoint, json=update_payload, timeout=40)
            
            if response.ok:
                logger.info(f"✅ Google News meta tags adicionadas | Post ID: {post_id} | Keywords: {keywords[:50]}...")
                logger.debug(f"   Genres: {genres}")
                return True
            else:
                logger.warning(
                    f"⚠️  Aviso ao adicionar Google News meta para post {post_id} | "
                    f"Status: {response.status_code}"
                )
                # Não retorna False pois isso não é crítico
                return True
                
        except requests.RequestException as e:
            logger.warning(f"⚠️  Aviso ao adicionar Google News meta: {type(e).__name__}")
            return True  # Não bloqueia se falhar

    def sanitize_published_post(self, post_id: int, max_attempts: int = 2, backoff_s: int = 2) -> bool:
        """
        Fetches the published post's content and excerpt, detects forbidden CTAs,
        attempts to sanitize them (content + excerpt) and updates the post via API.

        Returns True if an update was applied (or no CTA present). False if update failed.
        """
        endpoint = f"{self.api_url}/posts/{post_id}"
        params = {"context": "edit", "_fields": "content,excerpt"}

        try:
            r = self.session.get(endpoint, params=params, timeout=30)
            r.raise_for_status()
            data = r.json() or {}
        except requests.RequestException as e:
            logger.error(f"Failed to fetch post {post_id} for sanitation: {e}")
            if getattr(e, 'response', None) is not None:
                logger.error(f"Response body: {e.response.text}")
            return False

        content_obj = data.get('content') or {}
        excerpt_obj = data.get('excerpt') or {}
        content_raw = content_obj.get('raw') or content_obj.get('rendered') or ''
        excerpt_raw = excerpt_obj.get('raw') or excerpt_obj.get('rendered') or ''

        # Normalize HTML entities to increase detection coverage
        content_raw = _html.unescape(content_raw)
        excerpt_raw = _html.unescape(excerpt_raw)

        content_cta = detect_forbidden_cta(content_raw)
        excerpt_cta = detect_forbidden_cta(excerpt_raw)

        if not content_cta and not excerpt_cta:
            logger.debug(f"No CTA detected for post {post_id} (content/excerpt).")
            return True

        logger.warning(f"CTA detected in published post {post_id}: content_cta={content_cta} excerpt_cta={excerpt_cta}")

        # Attempt sanitization
        new_content, content_removed = strip_forbidden_cta_sentences(content_raw)
        new_excerpt, excerpt_removed = strip_forbidden_cta_sentences(excerpt_raw)

        # Fallback: aggressive simple string replacements for common variants
        def aggressive_fallback(s: str) -> str:
            if not s:
                return s
            s = s.replace("don\'t forget to subscribe", "")
            s = s.replace("don’t forget to subscribe", "")
            s = s.replace("don't forget to subscribe", "")
            s = s.replace("Thank you for reading this post, don't forget to subscribe!", "")
            s = s.replace("Thank you for reading this post, dont forget to subscribe!", "")
            # remove common English CTA fragments
            s = re.sub(r"(?is)thank\s+you\s+for\s+reading[^<]{0,200}?subscribe[^<]{0,200}?", "", s)
            s = re.sub(r"(?is)thanks\s+for\s+reading[^<]{0,200}?subscribe[^<]{0,200}?", "", s)
            return s

        if not content_removed:
            fallback_content = aggressive_fallback(new_content or content_raw)
            if fallback_content != (new_content or content_raw):
                new_content = fallback_content
                content_removed = True

        if not excerpt_removed:
            fallback_excerpt = aggressive_fallback(new_excerpt or excerpt_raw)
            if fallback_excerpt != (new_excerpt or excerpt_raw):
                new_excerpt = fallback_excerpt
                excerpt_removed = True

        if not content_removed and not excerpt_removed:
            logger.error(f"Sanitization attempted for post {post_id} but no removals applied. Will still attempt update if user requested.")

        payload = {}
        if content_removed and new_content is not None:
            payload['content'] = new_content
        if excerpt_removed and new_excerpt is not None:
            payload['excerpt'] = new_excerpt

        if not payload:
            # Nothing to update
            logger.info(f"No payload to update for post {post_id} after sanitation attempt.")
            return True

        # Try updating with retries
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            try:
                r = self.session.post(endpoint, json=payload, timeout=40)
                if r.ok:
                    logger.info(f"Sanitation update applied to post {post_id} (attempt {attempt}).")
                    return True
                else:
                    logger.error(f"Failed to apply sanitation update to post {post_id} (attempt {attempt}): {r.status_code} - {r.text}")
            except requests.RequestException as e:
                logger.error(f"Error applying sanitation update to post {post_id} (attempt {attempt}): {e}")
            time.sleep(backoff_s * attempt)

        logger.error(f"All attempts to sanitize post {post_id} failed.")
        return False

    def get_published_posts(self, fields: List[str], max_posts: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetches published posts, handling pagination, with an optional limit.

        Args:
            fields: A list of fields to retrieve for each post.
            max_posts: Optional limit on the total number of posts to fetch.
        """
        all_posts = []
        page = 1
        per_page = 100
        
        fields_str = ','.join(fields)

        while True:
            # Exit if we have reached the desired number of posts
            if max_posts and len(all_posts) >= max_posts:
                logger.info(f"Reached max_posts limit of {max_posts}. Stopping fetch.")
                break

            endpoint = f"{self.api_url}/posts"
            params = {
                "status": "publish",
                "per_page": per_page,
                "page": page,
                "_fields": fields_str,
            }
            try:
                logger.info(f"Fetching page {page} of published posts...")
                r = self.session.get(endpoint, params=params, timeout=30)
                r.raise_for_status()
                
                posts = r.json()
                if not posts:
                    logger.info("No more posts found. Finished fetching.")
                    break
                
                all_posts.extend(posts)
                
                if len(posts) < per_page:
                    logger.info(f"Last page reached ({len(posts)} posts). Finished fetching.")
                    break
                    
                page += 1

            except requests.RequestException as e:
                logger.error(f"Error fetching published posts (page {page}): {e}")
                if e.response is not None:
                    logger.error(f"Response body: {e.response.text}")
                break
        
        # Trim the list to the exact number if max_posts is set
        if max_posts:
            all_posts = all_posts[:max_posts]

        logger.info(f"Successfully fetched a total of {len(all_posts)} posts.")
        return all_posts

    def get_tags_map_by_ids(self, tag_ids: List[int]) -> Dict[int, str]:
        """ 
        Fetches tag details from a list of IDs and returns a map of {id: name}.
        Handles pagination for large lists of IDs.
        """
        if not tag_ids:
            return {}

        tag_map = {}
        unique_ids = list(set(tag_ids))
        endpoint = f"{self.api_url}/tags"
        
        # The 'include' parameter can take a list of up to 100 IDs.
        # We chunk the requests to handle more than 100.
        for i in range(0, len(unique_ids), 100):
            chunk = unique_ids[i:i + 100]
            params = {
                "include": ",".join(map(str, chunk)),
                "per_page": 100, # Ensure we get all requested items in the chunk
                "_fields": "id,name"
            }
            try:
                logger.info(f"Fetching names for {len(chunk)} tag IDs...")
                r = self.session.get(endpoint, params=params, timeout=30)
                r.raise_for_status()
                tags_data = r.json()
                for tag in tags_data:
                    tag_map[tag['id']] = tag['name']
            except requests.RequestException as e:
                logger.error(f"Error fetching tag details: {e}")
                # Continue to next chunk even if one fails
                continue
        
        logger.info(f"Successfully mapped {len(tag_map)} tag IDs to names.")
        return tag_map

    def close(self):
        """Closes the requests session."""
        self.session.close()