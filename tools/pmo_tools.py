from typing import List, Dict, Any
from langchain_core.tools import tool
from pmoskills import pmoskills, inject

@tool
def get_skills_list() -> List[Dict[str, Any]]:
    """Returns the active index of all PMBOK 8 executable skills.
    
    Returns:
        List[Dict[str, Any]]: A list of skill records containing their ID, title, and metadata.
    """
    return pmoskills.get_skills()

@tool
def get_skill_details(skill_id: str) -> Dict[str, Any]:
    """Gets execution steps, metadata, and template for a specific skill by its ID.
    
    Args:
        skill_id: The unique identifier of the skill (e.g., 'SKL-01-01').
        
    Returns:
        Dict[str, Any]: The detailed skill record.
    """
    skill = pmoskills.get_skill(skill_id)
    if not skill:
        raise ValueError(f"Skill {skill_id} not found.")
    return skill

@tool
def get_artifact_template(artifact_id: str) -> Dict[str, Any]:
    """Fetches the starting template content and metadata for a specific deliverable artifact by its ID.
    
    Args:
        artifact_id: The unique identifier of the artifact (e.g., 'A04').
        
    Returns:
        Dict[str, Any]: The artifact template record.
    """
    artifact = pmoskills.get_artifact(artifact_id)
    if not artifact:
        raise ValueError(f"Artifact {artifact_id} not found.")
    return artifact

@tool
def inject_template_parameters(prompt_text: str, params_dict: Dict[str, Any]) -> str:
    """Interpolates variables/parameters into the given template text using multiple placeholder formats.
    
    Args:
        prompt_text: The raw template text containing placeholders like [FIELD: name], [name], or {{name}}.
        params_dict: The dictionary of values to inject.
        
    Returns:
        str: The interpolated template string.
    """
    return inject(prompt_text, params_dict)
