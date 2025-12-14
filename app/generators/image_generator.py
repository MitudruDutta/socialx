import torch
from loguru import logger
from app.config import settings
from datetime import datetime
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from io import BytesIO
from PIL import Image


class ImageGenerator:
    """Generate images using Nano Banana (lightweight model)"""
    
    _executor = ThreadPoolExecutor(max_workers=1)  # Single thread for GPU ops
    
    def __init__(self):
        self.output_dir = settings.DATA_DIR / "generated_images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pipe = None
        self.device = settings.IMAGE_DEVICE
    
    def _load_model(self):
        """Load model synchronously (called in thread)"""
        if self.pipe is not None:
            return
        
        logger.info("Loading Nano Banana model...")
        from diffusers import AutoPipelineForText2Image
        
        self.pipe = AutoPipelineForText2Image.from_pretrained(
            "Blib-la/sd-turbo-banana",
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            variant="fp16" if self.device == "cuda" else None
        )
        self.pipe = self.pipe.to(self.device)
        
        if self.device == "cuda":
            self.pipe.enable_attention_slicing()
        
        logger.success("Nano Banana model loaded")
    
    def _generate_sync(self, prompt: str, negative_prompt: str, width: int, height: int, steps: int):
        """Synchronous generation (runs in thread pool)"""
        self._load_model()
        
        result = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=0.0
        )
        
        if not result.images:
            raise RuntimeError("Image generation returned no images")
            
        return result.images[0]
    
    async def generate(self, prompt: str, width: int = 512, height: int = 512, steps: int = 4) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        try:
            enhanced_prompt = f"{prompt}, high quality, professional"
            negative_prompt = "low quality, blurry, distorted, watermark, text"
            
            logger.info(f"Generating image: {prompt[:50]}...")
            
            if settings.IMAGE_USE_LOCAL:
                return await self._generate_local(enhanced_prompt, negative_prompt, width, height, steps)
            else:
                return await self._generate_api(enhanced_prompt)
                
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise
    
    async def _generate_local(self, prompt: str, negative_prompt: str, width: int, height: int, steps: int) -> str:
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(
            self._executor,
            self._generate_sync,
            prompt, negative_prompt, width, height, steps
        )
        
        return self._save_image(image, prompt)
    
    async def _generate_api(self, prompt: str) -> str:
        """Fallback to free API"""
        import httpx
        
        # URL-encode the prompt
        encoded_prompt = quote(prompt, safe='')
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"https://image.pollinations.ai/prompt/{encoded_prompt}",
                follow_redirects=True
            )
            response.raise_for_status()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = settings.IMAGE_OUTPUT_FORMAT.lower().lstrip('.')
            filename = f"api_{timestamp}.{ext}"
            image_path = self.output_dir / filename
            
            # If format mismatch or simple save needed, check content
            # Pollinations returns JPEG or PNG typically.
            # We want to enforce settings.IMAGE_OUTPUT_FORMAT
            
            try:
                img = Image.open(BytesIO(response.content))
                img.save(image_path, format=settings.IMAGE_OUTPUT_FORMAT.upper())
            except Exception as e:
                logger.warning(f"Failed to convert/save API image via PIL: {e}. Writing raw bytes as backup.")
                # Fallback write raw if PIL fails (unlikely if valid image)
                image_path.write_bytes(response.content)
            
            logger.success(f"Image saved: {image_path}")
            return str(image_path)
    
    def _save_image(self, image, prompt: str) -> str:
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{prompt_hash}.{settings.IMAGE_OUTPUT_FORMAT}"
        
        image_path = self.output_dir / filename
        
        max_size = settings.IMAGE_MAX_SIZE
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size))
        
        image.save(image_path)
        logger.success(f"Image saved: {image_path}")
        return str(image_path)
    
    def unload_model(self):
        """Free GPU memory"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            if self.device == "cuda":
                torch.cuda.empty_cache()
            logger.info("Model unloaded, GPU memory freed")
    
    def cleanup_old_images(self, days: int = 7):
        import time
        cutoff = time.time() - (days * 86400)
        
        deleted = 0
        for f in self.output_dir.glob(f"*.{settings.IMAGE_OUTPUT_FORMAT}"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete {f}: {e}")
        
        logger.info(f"Cleaned up {deleted} old images")
    
    def __del__(self):
        """Cleanup on garbage collection"""
        self.unload_model()
