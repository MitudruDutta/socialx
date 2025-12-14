import torch
from pathlib import Path
from loguru import logger
from app.config import settings
from datetime import datetime
import hashlib
import asyncio

class ImageGenerator:
    """Generate images using Nano Banana (lightweight model)"""
    
    def __init__(self):
        self.output_dir = Path("data/generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pipe = None
        self.device = settings.IMAGE_DEVICE
        
    async def initialize(self):
        if self.pipe is not None:
            return
        
        try:
            logger.info("Loading Nano Banana model...")
            from diffusers import AutoPipelineForText2Image
            
            self.pipe = AutoPipelineForText2Image.from_pretrained(
                "Blib-la/sd-turbo-banana",  # Nano Banana model
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                variant="fp16" if self.device == "cuda" else None
            )
            self.pipe = self.pipe.to(self.device)
            
            if self.device == "cuda":
                self.pipe.enable_attention_slicing()
            
            logger.success("Nano Banana model loaded")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    async def generate(self, prompt: str, width: int = 512, height: int = 512, steps: int = 4) -> str:
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
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        image = await loop.run_in_executor(
            None,
            lambda: self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=0.0  # Nano Banana uses guidance_scale=0
            ).images[0]
        )
        
        return self._save_image(image, prompt)
    
    async def _generate_api(self, prompt: str) -> str:
        # Fallback to API if local not available
        import httpx
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Use a free API like Pollinations
            response = await client.get(
                f"https://image.pollinations.ai/prompt/{prompt}",
                follow_redirects=True
            )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = self.output_dir / f"api_{timestamp}.png"
            image_path.write_bytes(response.content)
            
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
    
    def cleanup_old_images(self, days: int = 7):
        import time
        cutoff = time.time() - (days * 86400)
        
        deleted = 0
        for f in self.output_dir.glob("*.png"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        
        logger.info(f"Cleaned up {deleted} old images")
