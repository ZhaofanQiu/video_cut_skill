"""Tests for motion graphics template engine."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from video_cut_skill.motion_graphics import (
    EasingFunction,
    EasingType,
    ShapeElement,
    ShapeStyle,
    ShapeType,
    TextAlign,
    TextAnimation,
    TextAnimationConfig,
    TextElement,
    TextStyle,
)
from video_cut_skill.template_engine import (
    MotionTemplate,
    ParameterType,
    TemplateEngine,
    TemplateParameter,
    TemplateType,
    create_lower_third,
    create_youtube_intro,
    render_template_quick,
)


class TestTemplateParameter:
    """Test TemplateParameter class."""
    
    def test_string_parameter_creation(self):
        """Test string parameter creation."""
        param = TemplateParameter(
            name="title",
            param_type=ParameterType.STRING,
            required=True,
            description="视频标题"
        )
        
        assert param.name == "title"
        assert param.param_type == ParameterType.STRING
        assert param.required is True
        assert param.description == "视频标题"
    
    def test_number_parameter_with_validation(self):
        """Test number parameter with validation."""
        param = TemplateParameter(
            name="duration",
            param_type=ParameterType.NUMBER,
            default=30,
            validation={"min": 10, "max": 300}
        )
        
        assert param.default == 30
        assert param.validation == {"min": 10, "max": 300}
    
    def test_color_parameter(self):
        """Test color parameter."""
        param = TemplateParameter(
            name="accent_color",
            param_type=ParameterType.COLOR,
            default="#FF0000"
        )
        
        assert param.param_type == ParameterType.COLOR
    
    def test_validate_string_value(self):
        """Test string value validation."""
        param = TemplateParameter(
            name="text",
            param_type=ParameterType.STRING,
            required=True
        )
        
        assert param.validate_value("hello") is True
        assert param.validate_value(123) is False
        assert param.validate_value(None) is False  # Required
    
    def test_validate_number_value(self):
        """Test number value validation."""
        param = TemplateParameter(
            name="count",
            param_type=ParameterType.NUMBER,
            validation={"min": 0, "max": 100}
        )
        
        assert param.validate_value(50) is True
        assert param.validate_value(-1) is False
        assert param.validate_value(101) is False
        assert param.validate_value("not a number") is False
    
    def test_validate_color_value(self):
        """Test color value validation."""
        param = TemplateParameter(
            name="color",
            param_type=ParameterType.COLOR
        )
        
        assert param.validate_value("#FF0000") is True
        assert param.validate_value("#ffffff") is True
        assert param.validate_value("#123ABC") is True
        assert param.validate_value("FF0000") is False  # Missing #
        assert param.validate_value("#FF00") is False   # Too short
        assert param.validate_value("red") is False     # Named colors not supported
    
    def test_validate_boolean_value(self):
        """Test boolean value validation."""
        param = TemplateParameter(
            name="enabled",
            param_type=ParameterType.BOOLEAN
        )
        
        assert param.validate_value(True) is True
        assert param.validate_value(False) is True
        assert param.validate_value("true") is False
        assert param.validate_value(1) is False
    
    def test_validate_select_value(self):
        """Test select value validation."""
        param = TemplateParameter(
            name="alignment",
            param_type=ParameterType.SELECT,
            options=["left", "center", "right"]
        )
        
        assert param.validate_value("center") is True
        assert param.validate_value("left") is True
        assert param.validate_value("top") is False


class TestMotionTemplate:
    """Test MotionTemplate class."""
    
    def test_template_creation(self):
        """Test template creation."""
        template = MotionTemplate(
            template_id="test_intro",
            name="Test Intro",
            template_type=TemplateType.INTRO,
            description="A test intro template",
            author="Test Author",
            duration=3.0,
            resolution=(1920, 1080),
            tags=["test", "intro"]
        )
        
        assert template.template_id == "test_intro"
        assert template.name == "Test Intro"
        assert template.template_type == TemplateType.INTRO
        assert template.version == "1.0"
        assert template.duration == 3.0
        assert template.resolution == (1920, 1080)
    
    def test_template_serialization(self):
        """Test template serialization to dict."""
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO,
            parameters=[
                TemplateParameter(
                    name="title",
                    param_type=ParameterType.STRING,
                    required=True
                )
            ],
            elements=[{"type": "text", "text": "{{title}}"}]
        )
        
        data = template.to_dict()
        
        assert data["template_id"] == "test"
        assert data["name"] == "Test"
        assert data["template_type"] == "intro"
        assert len(data["parameters"]) == 1
        assert data["parameters"][0]["name"] == "title"
    
    def test_template_deserialization(self):
        """Test template deserialization from dict."""
        data = {
            "template_id": "test",
            "name": "Test Template",
            "template_type": "intro",
            "version": "2.0",
            "parameters": [
                {
                    "name": "channel_name",
                    "type": "string",
                    "required": True,
                    "description": "Channel name"
                }
            ],
            "elements": [],
            "duration": 5.0
        }
        
        template = MotionTemplate.from_dict(data)
        
        assert template.template_id == "test"
        assert template.name == "Test Template"
        assert template.version == "2.0"
        assert len(template.parameters) == 1
        assert template.parameters[0].name == "channel_name"
        assert template.parameters[0].param_type == ParameterType.STRING
    
    def test_validate_parameters_success(self):
        """Test parameter validation - success case."""
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO,
            parameters=[
                TemplateParameter(
                    name="title",
                    param_type=ParameterType.STRING,
                    required=True
                ),
                TemplateParameter(
                    name="duration",
                    param_type=ParameterType.NUMBER,
                    required=False,
                    default=30
                )
            ]
        )
        
        values = {"title": "My Video"}
        valid, errors = template.validate_parameters(values)
        
        assert valid is True
        assert len(errors) == 0
    
    def test_validate_parameters_missing_required(self):
        """Test parameter validation - missing required."""
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO,
            parameters=[
                TemplateParameter(
                    name="title",
                    param_type=ParameterType.STRING,
                    required=True
                )
            ]
        )
        
        values = {}  # Missing required 'title'
        valid, errors = template.validate_parameters(values)
        
        assert valid is False
        assert len(errors) == 1
        assert "Missing required" in errors[0]
    
    def test_validate_parameters_invalid_value(self):
        """Test parameter validation - invalid value."""
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO,
            parameters=[
                TemplateParameter(
                    name="count",
                    param_type=ParameterType.NUMBER,
                    validation={"min": 0, "max": 10}
                )
            ]
        )
        
        values = {"count": 20}  # Out of range
        valid, errors = template.validate_parameters(values)
        
        assert valid is False
        assert len(errors) == 1
    
    def test_apply_parameters(self):
        """Test parameter application."""
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO,
            parameters=[
                TemplateParameter(
                    name="channel_name",
                    param_type=ParameterType.STRING,
                    required=True
                ),
                TemplateParameter(
                    name="accent_color",
                    param_type=ParameterType.COLOR,
                    default="#FF0000"
                )
            ],
            elements=[
                {"type": "text", "text": "{{channel_name}}"},
                {"type": "shape", "style": {"fill_color": "{{accent_color}}"}}
            ]
        )
        
        values = {"channel_name": "My Channel"}
        elements = template.apply_parameters(values)
        
        assert elements[0]["text"] == "My Channel"
        assert elements[1]["style"]["fill_color"] == "#FF0000"
    
    def test_apply_parameters_with_provided_values(self):
        """Test parameter application with user-provided values."""
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO,
            parameters=[
                TemplateParameter(
                    name="accent_color",
                    param_type=ParameterType.COLOR,
                    default="#FF0000"
                )
            ],
            elements=[
                {"type": "shape", "style": {"fill_color": "{{accent_color}}"}}
            ]
        )
        
        values = {"accent_color": "#00FF00"}  # Override default
        elements = template.apply_parameters(values)
        
        assert elements[0]["style"]["fill_color"] == "#00FF00"


class TestTemplateEngine:
    """Test TemplateEngine class."""
    
    def test_initialization(self):
        """Test engine initialization."""
        engine = TemplateEngine()
        
        assert engine._templates is not None
        # Should have built-in templates
        assert len(engine._templates) >= 4
    
    def test_initialization_with_custom_dir(self):
        """Test engine initialization with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = TemplateEngine(template_dir=tmpdir)
            assert engine.template_dir == Path(tmpdir)
    
    def test_register_and_get_template(self):
        """Test template registration and retrieval."""
        engine = TemplateEngine()
        
        template = MotionTemplate(
            template_id="custom_template",
            name="Custom",
            template_type=TemplateType.CUSTOM
        )
        
        engine.register_template(template)
        
        retrieved = engine.get_template("custom_template")
        assert retrieved is not None
        assert retrieved.name == "Custom"
    
    def test_unregister_template(self):
        """Test template unregistration."""
        engine = TemplateEngine()
        
        template = MotionTemplate(
            template_id="temp_template",
            name="Temp",
            template_type=TemplateType.CUSTOM
        )
        
        engine.register_template(template)
        assert engine.get_template("temp_template") is not None
        
        result = engine.unregister_template("temp_template")
        assert result is True
        assert engine.get_template("temp_template") is None
    
    def test_unregister_nonexistent_template(self):
        """Test unregistering non-existent template."""
        engine = TemplateEngine()
        
        result = engine.unregister_template("nonexistent")
        assert result is False
    
    def test_list_templates(self):
        """Test listing templates."""
        engine = TemplateEngine()
        
        templates = engine.list_templates()
        assert len(templates) >= 4
    
    def test_list_templates_by_type(self):
        """Test listing templates by type."""
        engine = TemplateEngine()
        
        intro_templates = engine.list_templates(template_type=TemplateType.INTRO)
        assert len(intro_templates) >= 1
        assert all(t.template_type == TemplateType.INTRO for t in intro_templates)
    
    def test_list_templates_by_tags(self):
        """Test listing templates by tags."""
        engine = TemplateEngine()
        
        youtube_templates = engine.list_templates(tags=["youtube"])
        assert len(youtube_templates) >= 1
    
    def test_render_template_not_found(self):
        """Test rendering non-existent template."""
        engine = TemplateEngine()
        
        with pytest.raises(ValueError, match="Template not found"):
            engine.render_template("nonexistent", {})
    
    def test_render_template_invalid_parameters(self):
        """Test rendering with invalid parameters."""
        engine = TemplateEngine()
        
        with pytest.raises(ValueError, match="Invalid parameters"):
            engine.render_template("youtube_intro_v1", {})  # Missing required channel_name
    
    def test_render_youtube_intro_template(self):
        """Test rendering YouTube intro template."""
        engine = TemplateEngine()
        
        elements = engine.render_template(
            "youtube_intro_v1",
            {
                "channel_name": "Test Channel",
                "subtitle": "Subscribe for more",
                "accent_color": "#FF5733"
            }
        )
        
        assert len(elements) > 0
        # Should have text element with channel name
        text_elements = [e for e in elements if isinstance(e, TextElement)]
        assert len(text_elements) >= 1
    
    def test_render_lower_third_template(self):
        """Test rendering lower third template."""
        engine = TemplateEngine()
        
        elements = engine.render_template(
            "lower_third_v1",
            {
                "name": "John Doe",
                "title": "Software Engineer",
                "color": "#0066CC"
            }
        )
        
        assert len(elements) > 0
        # Should have shape and text elements
        shapes = [e for e in elements if isinstance(e, ShapeElement)]
        texts = [e for e in elements if isinstance(e, TextElement)]
        assert len(shapes) >= 1
        assert len(texts) >= 1
    
    def test_render_quote_card_template(self):
        """Test rendering quote card template."""
        engine = TemplateEngine()
        
        elements = engine.render_template(
            "quote_card_v1",
            {
                "quote": "Be the change you wish to see in the world.",
                "author": "Mahatma Gandhi"
            }
        )
        
        assert len(elements) > 0
    
    def test_render_title_card_template(self):
        """Test rendering title card template."""
        engine = TemplateEngine()
        
        elements = engine.render_template(
            "title_card_v1",
            {
                "title": "Introduction",
                "chapter_number": 1,
                "color": "#FFD700"
            }
        )
        
        assert len(elements) > 0
    
    def test_save_template_yaml(self):
        """Test saving template to YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = TemplateEngine(template_dir=tmpdir)
            
            template = MotionTemplate(
                template_id="test_save",
                name="Test Save",
                template_type=TemplateType.INTRO,
                parameters=[
                    TemplateParameter(
                        name="title",
                        param_type=ParameterType.STRING,
                        required=True
                    )
                ],
                elements=[{"type": "text", "text": "{{title}}"}]
            )
            
            filepath = engine.save_template(template, format="yaml")
            
            assert Path(filepath).exists()
            assert Path(filepath).suffix == ".yaml"
            
            # Verify content
            with open(filepath) as f:
                data = yaml.safe_load(f)
                assert data["template_id"] == "test_save"
    
    def test_save_template_json(self):
        """Test saving template to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = TemplateEngine(template_dir=tmpdir)
            
            template = MotionTemplate(
                template_id="test_json",
                name="Test JSON",
                template_type=TemplateType.INTRO
            )
            
            filepath = engine.save_template(template, format="json")
            
            assert Path(filepath).exists()
            assert Path(filepath).suffix == ".json"
            
            with open(filepath) as f:
                data = json.load(f)
                assert data["template_id"] == "test_json"
    
    def test_save_template_without_dir(self):
        """Test saving template without directory configured."""
        engine = TemplateEngine()  # No template_dir
        
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO
        )
        
        with pytest.raises(ValueError, match="Template directory not configured"):
            engine.save_template(template)
    
    def test_load_template_from_file_yaml(self):
        """Test loading template from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a template file
            data = {
                "template_id": "loaded_template",
                "name": "Loaded Template",
                "template_type": "intro",
                "parameters": [],
                "elements": [],
                "duration": 2.0
            }
            
            filepath = Path(tmpdir) / "test.yaml"
            with open(filepath, "w") as f:
                yaml.dump(data, f)
            
            engine = TemplateEngine()
            template = engine.load_template_from_file(filepath)
            
            assert template.template_id == "loaded_template"
            assert template.name == "Loaded Template"
            assert "loaded_template" in engine._templates
    
    def test_load_template_from_file_json(self):
        """Test loading template from JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "template_id": "json_template",
                "name": "JSON Template",
                "template_type": "intro",
                "parameters": [],
                "elements": []
            }
            
            filepath = Path(tmpdir) / "test.json"
            with open(filepath, "w") as f:
                json.dump(data, f)
            
            engine = TemplateEngine()
            template = engine.load_template_from_file(filepath)
            
            assert template.template_id == "json_template"
    
    def test_load_user_templates_on_init(self):
        """Test loading user templates on engine initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a user template
            data = {
                "template_id": "user_template",
                "name": "User Template",
                "template_type": "custom",
                "parameters": [],
                "elements": []
            }
            
            with open(Path(tmpdir) / "user.yaml", "w") as f:
                yaml.dump(data, f)
            
            engine = TemplateEngine(template_dir=tmpdir)
            
            assert engine.get_template("user_template") is not None


class TestBuiltinTemplates:
    """Test built-in templates."""
    
    def test_youtube_intro_template_exists(self):
        """Test YouTube intro template exists."""
        engine = TemplateEngine()
        
        template = engine.get_template("youtube_intro_v1")
        assert template is not None
        assert template.template_type == TemplateType.INTRO
        assert "youtube" in template.tags
    
    def test_youtube_intro_parameters(self):
        """Test YouTube intro template parameters."""
        engine = TemplateEngine()
        template = engine.get_template("youtube_intro_v1")
        
        param_names = [p.name for p in template.parameters]
        assert "channel_name" in param_names
        assert "accent_color" in param_names
        assert "subtitle" in param_names
    
    def test_lower_third_template_exists(self):
        """Test lower third template exists."""
        engine = TemplateEngine()
        
        template = engine.get_template("lower_third_v1")
        assert template is not None
        assert template.template_type == TemplateType.LOWER_THIRD
    
    def test_quote_card_template_exists(self):
        """Test quote card template exists."""
        engine = TemplateEngine()
        
        template = engine.get_template("quote_card_v1")
        assert template is not None
        assert template.template_type == TemplateType.QUOTE_CARD
    
    def test_title_card_template_exists(self):
        """Test title card template exists."""
        engine = TemplateEngine()
        
        template = engine.get_template("title_card_v1")
        assert template is not None
        assert template.template_type == TemplateType.TITLE_CARD


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_render_template_quick(self):
        """Test render_template_quick function."""
        elements = render_template_quick(
            "youtube_intro_v1",
            {"channel_name": "Test"}
        )
        
        assert len(elements) > 0
    
    def test_create_youtube_intro(self):
        """Test create_youtube_intro function."""
        elements = create_youtube_intro(
            channel_name="My Channel",
            subtitle="Subscribe!",
            accent_color="#00FF00"
        )
        
        assert len(elements) > 0
        # Check that parameters were applied
        text_elements = [e for e in elements if isinstance(e, TextElement)]
        assert any("My Channel" in str(e.text) for e in text_elements)
    
    def test_create_lower_third(self):
        """Test create_lower_third function."""
        elements = create_lower_third(
            name="Jane Smith",
            title="Product Manager",
            color="#FF5733"
        )
        
        assert len(elements) > 0


class TestTemplateParameterEdgeCases:
    """Test template parameter edge cases."""
    
    def test_optional_parameter_with_none_value(self):
        """Test optional parameter with None value."""
        param = TemplateParameter(
            name="optional",
            param_type=ParameterType.STRING,
            required=False
        )
        
        assert param.validate_value(None) is True
    
    def test_required_parameter_with_none_value(self):
        """Test required parameter with None value."""
        param = TemplateParameter(
            name="required",
            param_type=ParameterType.STRING,
            required=True
        )
        
        assert param.validate_value(None) is False
    
    def test_nested_placeholder_replacement(self):
        """Test nested placeholder replacement."""
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO,
            parameters=[
                TemplateParameter(name="title", param_type=ParameterType.STRING)
            ],
            elements=[
                {
                    "type": "text",
                    "text": "{{title}}",
                    "nested": {
                        "deep": "Value: {{title}}"
                    }
                }
            ]
        )
        
        elements = template.apply_parameters({"title": "Hello"})
        
        assert elements[0]["text"] == "Hello"
        assert elements[0]["nested"]["deep"] == "Value: Hello"
    
    def test_multiple_placeholders_same_element(self):
        """Test multiple placeholders in same element."""
        template = MotionTemplate(
            template_id="test",
            name="Test",
            template_type=TemplateType.INTRO,
            parameters=[
                TemplateParameter(name="first", param_type=ParameterType.STRING),
                TemplateParameter(name="second", param_type=ParameterType.STRING)
            ],
            elements=[
                {"type": "text", "text": "{{first}} and {{second}}"}
            ]
        )
        
        elements = template.apply_parameters(
            {"first": "A", "second": "B"}
        )
        
        assert elements[0]["text"] == "A and B"


class TestTemplateEngineErrorHandling:
    """Test template engine error handling."""
    
    def test_get_beat_markers_without_audio(self):
        """Test getting beat markers without loaded audio."""
        from video_cut_skill.beat_detection import BeatSyncEditor
        
        editor = BeatSyncEditor()
        
        with pytest.raises(ValueError, match="No audio loaded"):
            editor.get_beat_markers_for_export()
    
    def test_export_to_json_without_audio(self):
        """Test export without loaded audio."""
        from video_cut_skill.beat_detection import BeatSyncEditor
        
        editor = BeatSyncEditor()
        
        with pytest.raises(ValueError, match="No audio loaded"):
            editor.export_to_json("output.json")
